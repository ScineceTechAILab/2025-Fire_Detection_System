import time
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO
import logging
from collections import deque

# 可选依赖 torch，用于检测 CUDA 可用性与模型迁移
try:
    import torch
    _TORCH_AVAILABLE = True
except Exception:
    _TORCH_AVAILABLE = False

try:
    from config import CONFIDENCE_THRESHOLD, CAMERA_INDEX  # type: ignore
except Exception:
    CONFIDENCE_THRESHOLD = 0.8
    CAMERA_INDEX = 0


class Detector:
    """
    类级注释：火焰检测器
    结合YOLO目标检测和火焰特征验证，提高检测准确率
    
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
        self.weights_path = weights_path
        self.conf = float(conf) if conf is not None else CONFIDENCE_THRESHOLD
        self.device = device
        self.classes = classes
        self.imgsz = imgsz
        
        # 火焰特征验证参数
        self.min_fire_area = 500  # 最小火焰面积（像素）
        self.max_fire_area = 500000  # 最大火焰面积（像素）
        
        # 火焰颜色范围（HSV空间）
        # 红色火焰有两个范围：低红色(0-10)和高红色(170-180)
        self.fire_color_low1 = np.array([0, 100, 100])
        self.fire_color_high1 = np.array([10, 255, 255])
        self.fire_color_low2 = np.array([170, 100, 100])
        self.fire_color_high2 = np.array([180, 255, 255])
        
        # 橙色/黄色火焰补充
        self.fire_color_low3 = np.array([10, 100, 100])
        self.fire_color_high3 = np.array([35, 255, 255])
        
        # 动态检测：记录最近几帧的检测结果
        self.detection_history = deque(maxlen=10)  # 最近10帧的检测历史
        self.area_history = deque(maxlen=10)  # 最近10帧的面积变化

        self.logger.info(f"初始化 Detector: weights={self.weights_path}, conf={self.conf}, device={self.device}")
        self.model = self._load_model()

    def _check_gpu_availability(self):
        """
        函数级注释：检查并打印 GPU 使用信息
        用于验证系统是否真正使用了 GPU
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
                memory_total = device_prop.total_memory / (1024 ** 3)  # GB
                memory_allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)  # GB
                memory_reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)  # GB
                
                self.logger.info(f"   GPU {i}: {device_name}")
                self.logger.info(f"      总显存: {memory_total:.2f} GB")
                self.logger.info(f"      已分配: {memory_allocated:.2f} GB")
                self.logger.info(f"      已预留: {memory_reserved:.2f} GB")
        else:
            self.logger.warning("❌ CUDA 不可用，正在使用 CPU")
        
        self.logger.info("=" * 50)
    
    def _load_model(self) -> YOLO:
        try:
            # 先检查 GPU 可用性并打印信息
            self._check_gpu_availability()
            
            model = YOLO(self.weights_path)
            # 尝试将模型迁移到指定设备
            target = self.device
            if target and "cuda" in str(target).lower():
                if not _TORCH_AVAILABLE or not getattr(__import__("torch"), "cuda").is_available():
                    self.logger.warning("请求使用 GPU，但 CUDA 不可用，回退到 CPU")
                    target = "cpu"
            try:
                # ultralytics YOLO 支持 .to(device)
                model.to(target)
                self.logger.info(f"模型已迁移到设备: {target}")
            except Exception:
                # 若 .to 失败，记录但不阻塞（ultralytics 在内部可能已处理）
                self.logger.warning(f"将模型迁移到 {target} 失败（可忽略，如果 ulralytics 自动管理设备）")
            
            # 再次打印 GPU 信息（模型加载后）
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

    def detect_frame(self, frame: np.ndarray, draw: bool = True, return_time: bool = False) -> Tuple[np.ndarray, List[Dict]]:
        if frame is None:
            raise ValueError("输入 frame 为空")

        start = time.time()
        results = self.model.predict(source=frame, conf=self.conf, classes=self.classes, imgsz=self.imgsz, verbose=False)
        elapsed = time.time() - start

        detections: List[Dict] = []
        annotated = frame.copy() if draw else frame
        
        # 当前帧的有效检测数
        valid_fire_count = 0

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
                    xyxy = np.array([])
                    confs = np.array([])
                    clss = np.array([])

                for box, conf, cls in zip(xyxy, confs, clss):
                    det = self._format_result(box.tolist(), float(conf), int(cls), cls_names)
                    
                    # 仅对火焰类检测进行验证
                    if det.get('cls_name', '').lower() == 'fire':
                        # 火焰特征验证
                        if self._validate_fire(frame, det):
                            detections.append(det)
                            valid_fire_count += 1
                            if draw:
                                self._draw_box(annotated, det, is_valid=True)
                        else:
                            # 无效检测，画灰色框标记（可选）
                            if draw:
                                self._draw_box(annotated, det, is_valid=False)
                    else:
                        # 非火焰类直接添加
                        detections.append(det)
                        if draw:
                            self._draw_box(annotated, det)
        
        # 记录检测历史用于动态分析
        self.detection_history.append(valid_fire_count)
        
        # 计算当前帧的总面积（如果有多个检测）
        total_area = sum((d['xmax'] - d['xmin']) * (d['ymax'] - d['ymin']) for d in detections if d.get('cls_name', '').lower() == 'fire')
        self.area_history.append(total_area)

        if return_time:
            return annotated, detections, elapsed
        return annotated, detections
    
    def _validate_fire(self, frame: np.ndarray, det: Dict) -> bool:
        """
        函数级注释：验证检测框是否为真实火焰
        通过颜色、面积、形状等特征进行二次验证
        
        :param frame: 原始图像
        :param det: 检测结果
        :return: 是否为有效火焰
        """
        xmin, ymin, xmax, ymax = det['xmin'], det['ymin'], det['xmax'], det['ymax']
        
        # 1. 面积验证
        area = (xmax - xmin) * (ymax - ymin)
        if area < self.min_fire_area or area > self.max_fire_area:
            self.logger.debug(f"火焰验证失败：面积不符合 {area}")
            return False
        
        # 2. 提取ROI区域
        roi = frame[ymin:ymax, xmin:xmax]
        if roi.size == 0:
            return False
        
        # 3. 颜色验证（HSV空间）
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # 创建三个颜色范围的掩码
        mask1 = cv2.inRange(hsv, self.fire_color_low1, self.fire_color_high1)
        mask2 = cv2.inRange(hsv, self.fire_color_low2, self.fire_color_high2)
        mask3 = cv2.inRange(hsv, self.fire_color_low3, self.fire_color_high3)
        
        # 合并掩码
        fire_mask = cv2.bitwise_or(mask1, mask2)
        fire_mask = cv2.bitwise_or(fire_mask, mask3)
        
        # 计算火焰颜色像素占比
        fire_pixels = cv2.countNonZero(fire_mask)
        total_pixels = roi.shape[0] * roi.shape[1]
        fire_ratio = fire_pixels / total_pixels if total_pixels > 0 else 0
        
        # 火焰颜色像素占比至少10%
        if fire_ratio < 0.1:
            self.logger.debug(f"火焰验证失败：颜色占比不足 {fire_ratio:.2f}")
            return False
        
        # 4. 形状验证：火焰通常是不规则的，长宽比不会太极端
        width = xmax - xmin
        height = ymax - ymin
        aspect_ratio = width / height if height > 0 else 0
        
        # 长宽比在0.2到5之间比较合理
        if aspect_ratio < 0.2 or aspect_ratio > 5.0:
            self.logger.debug(f"火焰验证失败：长宽比异常 {aspect_ratio:.2f}")
            return False
        
        # 5. 亮度验证：火焰通常比较亮
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        
        # 平均亮度至少80（0-255）
        if avg_brightness < 80:
            self.logger.debug(f"火焰验证失败：亮度不足 {avg_brightness:.1f}")
            return False
        
        # 6. 动态验证：如果有历史数据，检查面积变化（火焰通常会闪烁/变化）
        if len(self.area_history) >= 3:
            # 计算最近几帧的面积变化率
            recent_areas = list(self.area_history)[-3:]
            if len(recent_areas) >= 2:
                changes = []
                for i in range(1, len(recent_areas)):
                    if recent_areas[i-1] > 0:
                        change = abs(recent_areas[i] - recent_areas[i-1]) / recent_areas[i-1]
                        changes.append(change)
                
                # 如果有历史检测且面积变化很小，可能是静止的光源（如鼠标灯）
                if changes and max(changes) < 0.05 and len(self.detection_history) >= 5:
                    # 检查是否连续多帧都有检测且变化极小
                    consistent_detections = sum(1 for cnt in self.detection_history if cnt > 0)
                    if consistent_detections >= 5:
                        self.logger.debug(f"火焰验证失败：疑似静止光源")
                        return False
        
        self.logger.debug(f"火焰验证通过：面积={area}, 颜色占比={fire_ratio:.2f}, 亮度={avg_brightness:.1f}")
        return True

    def _draw_box(self, img: np.ndarray, det: Dict, is_valid: bool = True):
        """
        函数级注释：绘制检测框
        
        :param img: 图像
        :param det: 检测结果
        :param is_valid: 是否为有效检测（影响颜色）
        """
        if is_valid:
            color = (0, 0, 255)  # 有效火焰：红色
        else:
            color = (128, 128, 128)  # 无效检测：灰色
        
        cv2.rectangle(img, (det["xmin"], det["ymin"]), (det["xmax"], det["ymax"]), color, 2)
        label = f'{det["cls_name"]} {det["conf"]:.2f}'
        if not is_valid:
            label += " (无效)"
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y0 = max(det["ymin"], h + 6)
        cv2.rectangle(img, (det["xmin"], y0 - h - 6), (det["xmin"] + w, y0), color, -1)
        cv2.putText(img, label, (det["xmin"], y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
