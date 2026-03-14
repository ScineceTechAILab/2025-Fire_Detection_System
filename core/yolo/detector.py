import time
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO
import logging
import sys
import math
import os

# 可选依赖 torch，用于检测 CUDA 可用性与模型迁移
try:
    import torch
    _TORCH_AVAILABLE = True
    
    # 关闭 PyTorch 2.6+ 默认开启的 weights_only
    import os
    os.environ["TORCH_FORCE_WEIGHTS_ONLY"] = "0"
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
         
except Exception as e:
    _TORCH_AVAILABLE = False

try:
    from config import CONFIDENCE_THRESHOLD, CAMERA_INDEX  # type: ignore
except Exception:
    CONFIDENCE_THRESHOLD = 0.8
    CAMERA_INDEX = 0


class Detector:
    """
    类级注释：高级火焰检测器 (V2.0)
    包含多模态验证、人形/手持物过滤、三级预警体系、光照补偿与动态背景更新。
    
    用法:
        det = Detector(weights_path="weights/best.pt", conf=0.4, device="cuda")
        annotated, detections = det.detect_frame(frame, draw=True)
    """

    def __init__(
        self,
        weights_path: Optional[str] = "weights/best.pt",
        conf: float = CONFIDENCE_THRESHOLD,
        device: str = "cpu",
        classes: Optional[List[int]] = None,
        imgsz: int = 640,
    ):
        self.logger = logging.getLogger("Detector")
        # 配置 Detector logger 只输出到控制台，不输出到文件
        self.logger.propagate = False
        # 添加控制台处理器
        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)
        
        self.weights_path = weights_path
        self.conf = float(conf) if conf is not None else CONFIDENCE_THRESHOLD
        self.device = device
        self.classes = classes
        self.imgsz = imgsz
        
        # ==========================================
        # 1. 动态背景与光照补偿模块
        # ==========================================
        # 用于适应不同光照条件，增强对比度
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        # 用于提取动态纹理，过滤静态照片
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=25, detectShadows=False)
        
        # ==========================================
        # 2. 火焰颜色模型 (HSV) 
        # ==========================================
        self.fire_color_low1 = np.array([0, 50, 50])
        self.fire_color_high1 = np.array([15, 255, 255])
        self.fire_color_low2 = np.array([165, 50, 50])
        self.fire_color_high2 = np.array([180, 255, 255])
        self.fire_color_low3 = np.array([10, 50, 50])
        self.fire_color_high3 = np.array([40, 255, 255])
        
        # ==========================================
        # 3. 三级预警体系追踪器
        # ==========================================
        # 记录格式: { track_id: {'centroid': (x,y), 'frames': 连续帧数, 'misses': 丢失帧数} }
        self.tracked_targets = {}
        self.next_track_id = 0

        # 初始化人脸检测器 (Haar Cascade) 用于二次过滤
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                self.logger.info(f"已加载人脸检测器: {cascade_path}")
            else:
                self.face_cascade = None
                self.logger.warning("未找到人脸检测模型，将仅依赖肤色阈值过滤")
        except Exception as e:
            self.face_cascade = None
            self.logger.warning(f"加载人脸检测器失败: {e}")

        self.logger.info(f"初始化高级 Detector V2.0: weights={self.weights_path}, conf={self.conf}, device={self.device}")
        self.model = self._load_model()

    def _check_gpu_availability(self):
        """
        函数级注释：检查并打印 GPU 使用信息
        """
        if not _TORCH_AVAILABLE:
            self.logger.info("PyTorch 不可用，无法检测 GPU")
            return
        
        torch = __import__("torch")
        self.logger.info("=" * 50)
        self.logger.info("GPU 使用情况验证")
        self.logger.info("=" * 50)
        
        if torch.cuda.is_available():
            self.logger.info(f"✅ CUDA 可用")
            self.logger.info(f"   CUDA 版本: {torch.version.cuda}")
            self.logger.info(f"   GPU 数量: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                device_name = torch.cuda.get_device_name(i)
                device_prop = torch.cuda.get_device_properties(i)
                memory_total = device_prop.total_memory / (1024 ** 3)
                memory_allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)
                memory_reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
                
                self.logger.info(f"   GPU {i}: {device_name}")
                self.logger.info(f"      总显存: {memory_total:.2f} GB")
                self.logger.info(f"      已分配: {memory_allocated:.2f} GB")
                self.logger.info(f"      已预留: {memory_reserved:.2f} GB")
        else:
            self.logger.warning("❌ CUDA 不可用，正在使用 CPU")
        
        self.logger.info("=" * 50)
    
    def _load_model(self) -> YOLO:
        try:
            self._check_gpu_availability()
            model = YOLO(self.weights_path)
            target = self.device
            if target and "cuda" in str(target).lower():
                if not _TORCH_AVAILABLE or not getattr(__import__("torch"), "cuda").is_available():
                    self.logger.warning("请求使用 GPU，但 CUDA 不可用，回退到 CPU")
                    target = "cpu"
            try:
                model.to(target)
                self.logger.info(f"模型已迁移到设备: {target}")
            except Exception:
                self.logger.warning(f"将模型迁移到 {target} 失败（可忽略）")
            
            self._check_gpu_availability()
            self.logger.info("YOLO 模型加载成功")
            return model
        except Exception as e:
            self.logger.exception(f"模型加载失败: {e}")
            raise

    def _format_result(self, box: List[float], conf: float, cls: int, names: Dict[int, str]) -> Dict:
        xmin, ymin, xmax, ymax = map(int, box)
        return {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "conf": float(conf),
            "cls_id": int(cls),
            "cls_name": names.get(int(cls), str(int(cls))),
        }

    def detect_frame(self, frame: np.ndarray, draw: bool = True, return_time: bool = False, is_static_test: bool = False) -> Tuple[np.ndarray, List[Dict]]:
        if frame is None:
            raise ValueError("输入 frame 为空")

        # ---------------------------------------------------------
        # A. 预处理：光照补偿与背景提取
        # ---------------------------------------------------------
        # 提取前景掩码（用于检测动态变化，过滤静态照片）
        # 如果是静态图片测试模式，则跳过背景建模更新，避免全黑掩码
        if not is_static_test:
            fg_mask = self.bg_subtractor.apply(frame)
        else:
            # 静态测试时，无法计算运动，我们生成一个全白掩码模拟"有运动"，或者在验证阶段跳过运动检查
            fg_mask = np.ones(frame.shape[:2], dtype=np.uint8) * 255
        
        # 光照补偿：转换到 YUV 空间并对亮度通道进行 CLAHE 直方图均衡化
        yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        yuv[:,:,0] = self.clahe.apply(yuv[:,:,0])
        enhanced_frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

        # ---------------------------------------------------------
        # B. YOLO 目标检测
        # ---------------------------------------------------------
        start = time.time()
        results = self.model.predict(source=enhanced_frame, conf=self.conf, classes=self.classes, imgsz=self.imgsz, verbose=False)
        elapsed = time.time() - start

        detections: List[Dict] = []
        annotated = frame.copy() if draw else frame
        current_fire_candidates = []

        if results and len(results) > 0:
            res = results[0]
            try:
                cls_names = res.names if hasattr(res, "names") and res.names else (self.model.names if hasattr(self.model, "names") else {})
            except Exception:
                cls_names = {}

            boxes = getattr(res, "boxes", None)
            if boxes is not None:
                try:
                    xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else np.array(boxes.xyxy)
                    confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.array(boxes.conf)
                    clss = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else np.array(boxes.cls)
                except Exception:
                    xyxy, confs, clss = np.array([]), np.array([]), np.array([])

                for box, conf, cls in zip(xyxy, confs, clss):
                    det = self._format_result(box.tolist(), float(conf), int(cls), cls_names)
                    cls_name_lower = det.get('cls_name', '').lower()
                    
                    if cls_name_lower == 'fire':
                        # ---------------------------------------------------------
                        # C1. 火焰多模态交叉验证
                        # ---------------------------------------------------------
                        is_valid = self._validate_fire(frame, enhanced_frame, fg_mask, det, skip_motion_check=is_static_test)
                        if is_valid:
                            current_fire_candidates.append(det)
                        else:
                            if draw: self._draw_box(annotated, det, level=0) # 无效：灰框
                            
                    elif cls_name_lower == 'smoke':
                        # ---------------------------------------------------------
                        # C2. 烟雾多模态交叉验证 (过滤加湿器水汽)
                        # ---------------------------------------------------------
                        is_valid = self._validate_smoke(frame, det)
                        if is_valid:
                            # 为了统一三级预警追踪，把验证通过的烟雾也放入候选列表
                            # 可以用原来的 det['cls_name'] 保持 smoke
                            current_fire_candidates.append(det)
                        else:
                            if draw: self._draw_box(annotated, det, level=0) # 无效：灰框
                            
                    else:
                        detections.append(det)
                        if draw: self._draw_box(annotated, det, level=-1) # 其他目标：蓝框

        # ---------------------------------------------------------
        # D. 三级预警体系追踪
        # ---------------------------------------------------------
        if not is_static_test:
            confirmed_detections = self._update_tracker(current_fire_candidates)
        else:
            # 静态测试模式下，不使用帧数追踪器，只要通过了单帧验证直接视为确诊
            confirmed_detections = []
            for det in current_fire_candidates:
                det['warning_level'] = 3
                # 保持它原有的类别，不强制覆盖为 fire
                confirmed_detections.append(det)
        
        for det in confirmed_detections:
            detections.append(det)
            if draw:
                self._draw_box(annotated, det, level=det.get('warning_level', 1))

        if return_time:
            return annotated, detections, elapsed
        return annotated, detections
        
    def _update_tracker(self, current_detections: List[Dict]) -> List[Dict]:
        """
        函数级注释：中心点追踪与三级预警判定
        Level 1 (初级疑似): 刚发现的火焰，黄色框，状态不报警
        Level 2 (中级异常): 持续2-4帧，橙色框，状态不报警
        Level 3 (高级确认): 持续5帧以上，红色框，输出 'fire' 类触发主程序报警
        """
        updated_detections = []
        unmatched_tracks = set(self.tracked_targets.keys())
        
        for det in current_detections:
            cx = (det['xmin'] + det['xmax']) / 2
            cy = (det['ymin'] + det['ymax']) / 2
            
            # 寻找最近的追踪目标
            best_track_id = None
            min_dist = float('inf')
            for tid in list(unmatched_tracks):
                track = self.tracked_targets[tid]
                dist = math.hypot(cx - track['centroid'][0], cy - track['centroid'][1])
                # 距离阈值设定为 80 像素，适应目标移动
                if dist < 80:
                    if dist < min_dist:
                        min_dist = dist
                        best_track_id = tid
                        
            if best_track_id is not None:
                # 更新现有追踪
                self.tracked_targets[best_track_id]['centroid'] = (cx, cy)
                self.tracked_targets[best_track_id]['frames'] += 1
                self.tracked_targets[best_track_id]['misses'] = 0
                frames = self.tracked_targets[best_track_id]['frames']
                unmatched_tracks.remove(best_track_id)
            else:
                # 创建新追踪
                best_track_id = self.next_track_id
                self.tracked_targets[best_track_id] = {'centroid': (cx, cy), 'frames': 1, 'misses': 0}
                self.next_track_id += 1
                frames = 1
                
            # 三级预警判定逻辑
            original_cls = det.get('cls_name', 'fire')
            
            if frames >= 5:
                level = 3  # 高级确认 -> 立即触发警报
                # 保持原类别 (fire 或 smoke)，以便后续处理
            elif frames >= 2:
                level = 2  # 中级异常 -> 启动二次验证 (暂不报警)
                det['cls_name'] = f'suspected_{original_cls}'
            else:
                level = 1  # 初级疑似 -> 持续追踪 (暂不报警)
                det['cls_name'] = f'suspected_{original_cls}'
                
            det['warning_level'] = level
            updated_detections.append(det)
            
        # 清理丢失的追踪目标 (允许丢失3帧)
        for tid in list(unmatched_tracks):
            self.tracked_targets[tid]['misses'] += 1
            if self.tracked_targets[tid]['misses'] > 3:
                del self.tracked_targets[tid]
                
        return updated_detections

    def _validate_fire(self, raw_frame: np.ndarray, enhanced_frame: np.ndarray, fg_mask: np.ndarray, det: Dict, skip_motion_check: bool = False) -> bool:
        """
        函数级注释：多模态特征交叉验证，专治照片误报
        包括：动态纹理检测、人手肤色过滤、相框直线检测、轮廓复杂度分析
        """
        xmin, ymin, xmax, ymax = det['xmin'], det['ymin'], det['xmax'], det['ymax']
        width, height = xmax - xmin, ymax - ymin
        total_pixels = width * height
        
        if total_pixels < 200:
            return False
            
        roi_raw = raw_frame[ymin:ymax, xmin:xmax]
        roi_enhanced = enhanced_frame[ymin:ymax, xmin:xmax]
        if roi_raw.size == 0: return False

        # ==========================================
        # 1. 动态纹理检测 (运动比例)
        # ==========================================
        # 真实火焰会跳跃，照片如果是静止的，前景掩码几乎为0
        roi_fg = fg_mask[ymin:ymax, xmin:xmax]
        motion_ratio = cv2.countNonZero(roi_fg) / total_pixels

        # ==========================================
        # 2. 人形/手部肤色过滤 (YCrCb)
        # ==========================================
        ycrcb = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2YCrCb)
        
        # 优化肤色检测：结合亮度 (Y) 排除极亮的火焰
        # Y: 80~200 (排除过暗或过亮，火焰通常 Y > 200)
        # Cr: 133~173 (红红色度)
        # Cb: 77~127 (蓝蓝色度)
        skin_low = np.array([80, 135, 85])
        skin_high = np.array([200, 170, 125])
        skin_mask = cv2.inRange(ycrcb, skin_low, skin_high)
        skin_ratio = cv2.countNonZero(skin_mask) / total_pixels
        
        # 严格限制：如果边界框内大面积是皮肤，且不包含极亮区域，才判定为脸/手
        # 火焰照片可能也会有部分落在肤色区，所以我们提高阈值到 30% (原 40%)
        # 这里的 0.30 是经验值，针对低头看手机等场景进行了优化
        if skin_ratio > 0.30:
            self.logger.info(f"多模态过滤: 真实肤色占比过高 ({skin_ratio:.2f} > 0.30)，判定为人手/人脸")
            return False
            
        # 额外的人脸检测器校验 (Haar Cascade)
        # 如果肤色占比 > 15% 且 检测到人脸特征，直接过滤
        if self.face_cascade and skin_ratio > 0.15:
            # 转换为灰度图检测
            gray_roi_face = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2GRAY)
            # 适当放大搜索比例，检测正脸
            faces = self.face_cascade.detectMultiScale(gray_roi_face, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
            if len(faces) > 0:
                self.logger.info(f"多模态过滤: Haar级联检测器识别到人脸特征，判定为误报")
                return False

        # ==========================================
        # 3. 形状轮廓与手持物过滤 (直线边缘检测)
        # ==========================================
        gray_roi = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 50, 150)
        # 寻找直线，手机/照片边缘通常是长直线
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=40, minLineLength=min(width, height)*0.5, maxLineGap=10)
        
        if lines is not None and len(lines) >= 3:
            self.logger.info(f"多模态过滤: 检测到 {len(lines)} 条明显直线边缘，疑似相框/手机屏幕")
            return False
            
        # ==========================================
        # 4. 颜色温度分析 (结合增强图像)
        # ==========================================
        hsv = cv2.cvtColor(roi_enhanced, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.fire_color_low1, self.fire_color_high1)
        mask2 = cv2.inRange(hsv, self.fire_color_low2, self.fire_color_high2)
        mask3 = cv2.inRange(hsv, self.fire_color_low3, self.fire_color_high3)
        fire_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
        
        fire_ratio = cv2.countNonZero(fire_mask) / total_pixels
        if fire_ratio < 0.05:
            return False
            
        # ==========================================
        # 5. 轮廓复杂度识别
        # ==========================================
        # 真实火焰边缘极其不规则，照片通常是矩形
        contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        complexity = 0
        if contours:
            c = max(contours, key=cv2.contourArea)
            c_area = cv2.contourArea(c)
            if c_area > 50:
                perimeter = cv2.arcLength(c, True)
                complexity = (perimeter ** 2) / (4 * np.pi * c_area)
                
        # 完美的圆形复杂度约等于1，正方形约等于1.27
        if 0 < complexity < 1.3:
            self.logger.info(f"多模态过滤: 火焰轮廓过于规则 (复杂度 {complexity:.2f})，疑似人工图像")
            return False
            
        # ==========================================
        # 6. 动静结合终极校验
        # ==========================================
        # 如果是极度静止的物体，且形状不够复杂（照片在晃动时有运动，但形状规则）
        if not skip_motion_check:
            if motion_ratio < 0.05 and complexity < 2.0:
                 self.logger.info(f"多模态过滤: 静态目标且形状不符合真实火焰 (运动比 {motion_ratio:.2f})")
                 return False

        self.logger.info(f"火焰验证通过: 复杂度={complexity:.2f}, 运动比={motion_ratio:.2f}, 肤色={skin_ratio:.2f}")
        return True

    def _validate_smoke(self, raw_frame: np.ndarray, det: Dict) -> bool:
        """
        函数级注释：烟雾特征验证，专门过滤加湿器水汽、白色反光等
        水汽特征：饱和度极低，亮度极高，内部没有高频纹理（很平滑）
        火灾烟雾特征：通常夹杂灰/黑/黄色，有颗粒感（高频细节）
        """
        xmin, ymin, xmax, ymax = det['xmin'], det['ymin'], det['xmax'], det['ymax']
        width, height = xmax - xmin, ymax - ymin
        
        # 面积太小很难判断，直接放行或者过滤视需求而定，这里设定最小面积
        if width * height < 400:
            return False
            
        roi_raw = raw_frame[ymin:ymax, xmin:xmax]
        if roi_raw.size == 0: return False
        
        # ==========================================
        # 1. 亮度与饱和度分析 (HSV)
        # ==========================================
        hsv = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2HSV)
        s_channel = hsv[:, :, 1]
        v_channel = hsv[:, :, 2]
        
        avg_s = np.mean(s_channel)
        avg_v = np.mean(v_channel)
        
        # 加湿器水汽通常非常白（亮度极高，饱和度接近0）
        # 如果亮度超过 220 且饱和度小于 15，极大概率是纯白水汽或反光
        if avg_v > 210 and avg_s < 20:
            self.logger.info(f"烟雾验证失败：亮度极高({avg_v:.1f})且饱和度极低({avg_s:.1f})，疑似加湿器水汽或灯光")
            return False
            
        # ==========================================
        # 2. 纹理高频细节分析 (Laplacian 边缘检测方差)
        # ==========================================
        # 水汽内部非常平滑，边缘模糊；而浓烟内部有颗粒感，滚动时有明显的不规则纹理
        gray_roi = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_roi, cv2.CV_64F)
        variance = laplacian.var()
        
        # 完美的纯白墙面或浓密水汽方差很低 (< 50)
        # 真实环境中的烟雾由于透光不均、碳颗粒，方差通常较高
        if variance < 30:
            self.logger.info(f"烟雾验证失败：内部纹理过于平滑 (方差 {variance:.1f})，疑似水汽或纯色墙面")
            return False
            
        self.logger.info(f"烟雾验证通过: 亮度={avg_v:.1f}, 饱和度={avg_s:.1f}, 纹理方差={variance:.1f}")
        return True

    def _draw_box(self, img: np.ndarray, det: Dict, level: int = 1):
        """
        函数级注释：分级绘制检测框
        """
        if level == 3:
            color = (0, 0, 255) # 红色: 高级确认 (真实报警)
            status = " [L3: Confirmed]"
        elif level == 2:
            color = (0, 165, 255) # 橙色: 中级异常
            status = " [L2: Validating]"
        elif level == 1:
            color = (0, 255, 255) # 黄色: 初级疑似
            status = " [L1: Suspected]"
        elif level == 0:
            color = (128, 128, 128) # 灰色: 被规则过滤
            status = " [Filtered]"
        else:
            color = (255, 0, 0) # 蓝色: 其他类别
            status = ""
            
        cv2.rectangle(img, (det["xmin"], det["ymin"]), (det["xmax"], det["ymax"]), color, 2)
        label = f'{det["cls_name"]} {det["conf"]:.2f}{status}'
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y0 = max(det["ymin"], h + 6)
        cv2.rectangle(img, (det["xmin"], y0 - h - 6), (det["xmin"] + w, y0), color, -1)
        cv2.putText(img, label, (det["xmin"], y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
