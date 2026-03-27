import json
import time
from typing import List, Dict, Tuple, Optional, Any
import cv2
import numpy as np
from ultralytics import YOLO
import logging
import sys
import math
import os

# 导入项目统一的日志配置
try:
    from utils.logging_config import get_logger
except ImportError:
    get_logger = logging.getLogger

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
        self.logger = get_logger("Detector")
        
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
        self._runtime_config_signature = ""
        self._init_runtime_defaults()
        self._init_runtime_config_loader()
        self._refresh_runtime_config(force=True)

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

    def _init_runtime_defaults(self):
        self.yolo_iou_threshold = 0.45
        self.min_box_area = 200
        self.max_box_area = 500000
        self.fire_small_area_threshold = 1500
        self.fire_medium_area_threshold = 6000
        self.fire_small_target_fire_ratio_min = 0.10
        self.fire_medium_target_fire_ratio_min = 0.06
        self.fire_large_target_fire_ratio_min = 0.05
        self.fire_small_target_motion_min = 0.08
        self.fire_medium_target_motion_min = 0.05
        self.fire_large_target_motion_min = 0.04
        self.fire_small_target_vstd_min = 32.0
        self.fire_medium_target_vstd_min = 25.0
        self.fire_large_target_vstd_min = 22.0
        self.fire_small_target_confirm_frames = 7
        self.fire_small_target_jitter_min = 0.015
        self.fire_track_match_dist_px = 80
        self.fire_track_min_iou = 0.10
        self.fire_track_area_change_max = 2.0

    def _init_runtime_config_loader(self):
        self.config_loader = None
        try:
            from core.communication.config_hot_loader import get_config_hot_loader
            self.config_loader = get_config_hot_loader()
        except Exception as e:
            self.logger.warning(f"热加载配置不可用，使用默认参数: {e}")

    def _to_int(self, value: Any, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
        try:
            out = int(value)
        except Exception:
            return default
        if min_val is not None:
            out = max(min_val, out)
        if max_val is not None:
            out = min(max_val, out)
        return out

    def _to_float(
        self, value: Any, default: float, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> float:
        try:
            out = float(value)
        except Exception:
            return default
        if min_val is not None:
            out = max(min_val, out)
        if max_val is not None:
            out = min(max_val, out)
        return out

    def _refresh_runtime_config(self, force: bool = False):
        if not self.config_loader:
            return
        try:
            raw_cfg = {
                "yolo_iou_threshold": self.config_loader.get_config("yolo_iou_threshold", self.yolo_iou_threshold),
                "min_box_area": self.config_loader.get_config("min_box_area", self.min_box_area),
                "max_box_area": self.config_loader.get_config("max_box_area", self.max_box_area),
                "fire_small_area_threshold": self.config_loader.get_config("fire_small_area_threshold", self.fire_small_area_threshold),
                "fire_medium_area_threshold": self.config_loader.get_config("fire_medium_area_threshold", self.fire_medium_area_threshold),
                "fire_small_target_motion_min": self.config_loader.get_config("fire_small_target_motion_min", self.fire_small_target_motion_min),
                "fire_small_target_fire_ratio_min": self.config_loader.get_config("fire_small_target_fire_ratio_min", self.fire_small_target_fire_ratio_min),
                "fire_small_target_confirm_frames": self.config_loader.get_config("fire_small_target_confirm_frames", self.fire_small_target_confirm_frames),
                "fire_small_target_jitter_min": self.config_loader.get_config("fire_small_target_jitter_min", self.fire_small_target_jitter_min),
                "fire_track_match_dist_px": self.config_loader.get_config("fire_track_match_dist_px", self.fire_track_match_dist_px),
                "fire_track_min_iou": self.config_loader.get_config("fire_track_min_iou", self.fire_track_min_iou),
                "fire_track_area_change_max": self.config_loader.get_config("fire_track_area_change_max", self.fire_track_area_change_max),
            }
        except Exception as e:
            self.logger.warning(f"读取热配置失败: {e}")
            return

        signature = json.dumps(raw_cfg, sort_keys=True, ensure_ascii=False, default=str)
        if not force and signature == self._runtime_config_signature:
            return
        self._runtime_config_signature = signature

        self.yolo_iou_threshold = self._to_float(
            raw_cfg.get("yolo_iou_threshold"), self.yolo_iou_threshold, min_val=0.05, max_val=0.95
        )
        self.min_box_area = self._to_int(
            raw_cfg.get("min_box_area"), self.min_box_area, min_val=50, max_val=200000
        )
        self.max_box_area = self._to_int(
            raw_cfg.get("max_box_area"), self.max_box_area, min_val=1000, max_val=10000000
        )
        if self.max_box_area <= self.min_box_area:
            self.max_box_area = self.min_box_area + 1000

        self.fire_small_area_threshold = self._to_int(
            raw_cfg.get("fire_small_area_threshold"), self.fire_small_area_threshold, min_val=100, max_val=50000
        )
        self.fire_medium_area_threshold = self._to_int(
            raw_cfg.get("fire_medium_area_threshold"), self.fire_medium_area_threshold, min_val=500, max_val=300000
        )
        if self.fire_medium_area_threshold <= self.fire_small_area_threshold:
            self.fire_medium_area_threshold = self.fire_small_area_threshold + 1000

        self.fire_small_target_motion_min = self._to_float(
            raw_cfg.get("fire_small_target_motion_min"), self.fire_small_target_motion_min, min_val=0.0, max_val=1.0
        )
        self.fire_small_target_fire_ratio_min = self._to_float(
            raw_cfg.get("fire_small_target_fire_ratio_min"), self.fire_small_target_fire_ratio_min, min_val=0.0, max_val=1.0
        )
        self.fire_small_target_confirm_frames = self._to_int(
            raw_cfg.get("fire_small_target_confirm_frames"), self.fire_small_target_confirm_frames, min_val=5, max_val=20
        )
        self.fire_small_target_jitter_min = self._to_float(
            raw_cfg.get("fire_small_target_jitter_min"), self.fire_small_target_jitter_min, min_val=0.0, max_val=0.2
        )

        self.fire_track_match_dist_px = self._to_int(
            raw_cfg.get("fire_track_match_dist_px"), self.fire_track_match_dist_px, min_val=20, max_val=500
        )
        self.fire_track_min_iou = self._to_float(
            raw_cfg.get("fire_track_min_iou"), self.fire_track_min_iou, min_val=0.0, max_val=1.0
        )
        self.fire_track_area_change_max = self._to_float(
            raw_cfg.get("fire_track_area_change_max"), self.fire_track_area_change_max, min_val=1.0, max_val=20.0
        )

    def _clip_det_box(self, det: Dict, frame_shape: Tuple[int, ...]) -> Optional[Tuple[int, int, int, int]]:
        h, w = frame_shape[:2]
        xmin = max(0, min(w - 1, int(det.get("xmin", 0))))
        ymin = max(0, min(h - 1, int(det.get("ymin", 0))))
        xmax = max(0, min(w, int(det.get("xmax", 0))))
        ymax = max(0, min(h, int(det.get("ymax", 0))))
        if xmax <= xmin or ymax <= ymin:
            return None
        return xmin, ymin, xmax, ymax

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
            raise ValueError("输入帧为空")
        self._refresh_runtime_config(force=False)

        if not is_static_test:
            fg_mask = self.bg_subtractor.apply(frame)
        else:
            fg_mask = np.ones(frame.shape[:2], dtype=np.uint8) * 255

        yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        yuv[:, :, 0] = self.clahe.apply(yuv[:, :, 0])
        enhanced_frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

        start = time.time()
        try:
            results = self.model.predict(
                source=enhanced_frame,
                conf=self.conf,
                iou=self.yolo_iou_threshold,
                classes=self.classes,
                imgsz=self.imgsz,
                verbose=False,
            )
        except Exception as e:
            elapsed = time.time() - start
            self.logger.exception(f"YOLO 单帧推理失败: {e}")
            empty_dets: List[Dict] = []
            if return_time:
                return (frame.copy() if draw else frame), empty_dets, elapsed
            return (frame.copy() if draw else frame), empty_dets

        elapsed = time.time() - start

        detections: List[Dict] = []
        annotated = frame.copy() if draw else frame
        current_fire_candidates: List[Dict] = []

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
                        self.logger.info(f"YOLO检测到火灾: conf={det['conf']:.3f}, box=[{det['xmin']},{det['ymin']},{det['xmax']},{det['ymax']}]")
                        is_valid = self._validate_fire(frame, enhanced_frame, fg_mask, det, skip_motion_check=is_static_test)
                        if is_valid:
                            current_fire_candidates.append(det)
                        else:
                            if draw:
                                self._draw_box(annotated, det, level=0)

                    elif cls_name_lower == 'smoke':
                        # smoke 继续禁用，避免加湿器误报
                        pass

                    else:
                        detections.append(det)
                        if draw:
                            self._draw_box(annotated, det, level=-1)

        if not is_static_test:
            confirmed_detections = self._update_tracker(current_fire_candidates)
        else:
            confirmed_detections = []
            for det in current_fire_candidates:
                det['warning_level'] = 3
                confirmed_detections.append(det)

        for det in confirmed_detections:
            detections.append(det)
            if draw:
                self._draw_box(annotated, det, level=det.get('warning_level', 1))

        if return_time:
            return annotated, detections, elapsed
        return annotated, detections

    def _bbox_iou(self, a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
        inter_h = max(0, min(ay2, by2) - max(ay1, by1))
        inter = inter_w * inter_h
        if inter <= 0:
            return 0.0
        area_a = max((ax2 - ax1) * (ay2 - ay1), 1)
        area_b = max((bx2 - bx1) * (by2 - by1), 1)
        union = area_a + area_b - inter
        return float(inter / union) if union > 0 else 0.0

    def _match_track_score(self, track: Dict, det: Dict) -> Optional[float]:
        cx = (det['xmin'] + det['xmax']) / 2
        cy = (det['ymin'] + det['ymax']) / 2
        dist = math.hypot(cx - track['centroid'][0], cy - track['centroid'][1])
        if dist > self.fire_track_match_dist_px:
            return None

        det_bbox = (det['xmin'], det['ymin'], det['xmax'], det['ymax'])
        det_area = max((det['xmax'] - det['xmin']) * (det['ymax'] - det['ymin']), 1)

        track_bbox = track.get('bbox')
        track_area = float(track.get('area', det_area))
        iou = self._bbox_iou(track_bbox, det_bbox) if track_bbox else 0.0

        min_area = max(min(track_area, det_area), 1.0)
        max_area = max(track_area, det_area)
        area_ratio = max_area / min_area
        if area_ratio > self.fire_track_area_change_max:
            return None

        if iou < self.fire_track_min_iou and dist > self.fire_track_match_dist_px * 0.5:
            return None

        dist_score = max(0.0, 1.0 - dist / max(float(self.fire_track_match_dist_px), 1.0))
        area_score = max(0.0, 1.0 - (area_ratio - 1.0) / max(self.fire_track_area_change_max - 1.0, 1.0))
        score = 0.50 * dist_score + 0.35 * iou + 0.15 * area_score
        return score

    def _compute_track_jitter(self, history: List[Tuple[float, float, float]], current_box_diag: float) -> float:
        if len(history) < 3:
            return 0.0

        points = np.array([[h[0], h[1]] for h in history], dtype=np.float32)
        areas = np.array([h[2] for h in history], dtype=np.float32)

        center_steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
        center_jitter = float(np.std(center_steps)) / max(current_box_diag, 1.0)
        area_jitter = float(np.std(areas) / max(np.mean(areas), 1.0))
        return center_jitter + area_jitter

    def _update_tracker(self, current_detections: List[Dict]) -> List[Dict]:
        """
        基于中心点的追踪与三级预警升级。
        小目标在升到 L3 前需要满足抖动阈值。
        """
        updated_detections = []
        unmatched_tracks = set(self.tracked_targets.keys())

        for det in current_detections:
            det_area = max((det['xmax'] - det['xmin']) * (det['ymax'] - det['ymin']), 1)
            box_diag = math.hypot(det['xmax'] - det['xmin'], det['ymax'] - det['ymin'])
            det_bbox = (det['xmin'], det['ymin'], det['xmax'], det['ymax'])
            cx = (det['xmin'] + det['xmax']) / 2
            cy = (det['ymin'] + det['ymax']) / 2

            best_track_id = None
            best_score = -1.0
            for tid in list(unmatched_tracks):
                track = self.tracked_targets[tid]
                score = self._match_track_score(track, det)
                if score is None:
                    continue
                if score > best_score:
                    best_score = score
                    best_track_id = tid

            if best_track_id is not None:
                track = self.tracked_targets[best_track_id]
                track['centroid'] = (cx, cy)
                track['bbox'] = det_bbox
                track['area'] = float(det_area)
                track['frames'] += 1
                track['misses'] = 0
                history = track.get('history', [])
                history.append((cx, cy, float(det_area)))
                track['history'] = history[-8:]
                frames = track['frames']
                unmatched_tracks.remove(best_track_id)
            else:
                best_track_id = self.next_track_id
                self.tracked_targets[best_track_id] = {
                    'centroid': (cx, cy),
                    'bbox': det_bbox,
                    'area': float(det_area),
                    'frames': 1,
                    'misses': 0,
                    'history': [(cx, cy, float(det_area))],
                }
                self.next_track_id += 1
                frames = 1

            track = self.tracked_targets[best_track_id]
            jitter = self._compute_track_jitter(track.get('history', []), box_diag)
            is_small_target = det_area < self.fire_small_area_threshold
            confirm_frames = self.fire_small_target_confirm_frames if is_small_target else 5
            original_cls = det.get('cls_name', 'fire')

            if frames >= confirm_frames:
                if jitter < self.fire_small_target_jitter_min:
                    level = 2
                    det['cls_name'] = f'suspected_{original_cls}'
                    det['hold_reason'] = 'low_jitter'
                    self.logger.info(
                        f"目标抖动不足，维持在 L2: area={det_area}, jitter={jitter:.4f}, threshold={self.fire_small_target_jitter_min:.4f}"
                    )
                else:
                    level = 3
            elif frames >= 2:
                level = 2
                det['cls_name'] = f'suspected_{original_cls}'
            else:
                level = 1
                det['cls_name'] = f'suspected_{original_cls}'

            det['warning_level'] = level
            det['track_jitter'] = round(jitter, 4)
            det['track_frames'] = frames
            updated_detections.append(det)

        for tid in list(unmatched_tracks):
            self.tracked_targets[tid]['misses'] += 1
            if self.tracked_targets[tid]['misses'] > 3:
                del self.tracked_targets[tid]

        return updated_detections

    def _get_dynamic_fire_thresholds(self, total_pixels: int) -> Dict[str, Any]:
        if total_pixels < self.fire_small_area_threshold:
            return {
                'scale': 'small',
                'min_fire_ratio': self.fire_small_target_fire_ratio_min,
                'min_motion_ratio': self.fire_small_target_motion_min,
                'min_v_std': self.fire_small_target_vstd_min,
            }
        if total_pixels < self.fire_medium_area_threshold:
            return {
                'scale': 'medium',
                'min_fire_ratio': self.fire_medium_target_fire_ratio_min,
                'min_motion_ratio': self.fire_medium_target_motion_min,
                'min_v_std': self.fire_medium_target_vstd_min,
            }
        return {
            'scale': 'large',
            'min_fire_ratio': self.fire_large_target_fire_ratio_min,
            'min_motion_ratio': self.fire_large_target_motion_min,
            'min_v_std': self.fire_large_target_vstd_min,
        }

    def _is_yellow_object_false_alarm(
        self,
        roi_raw: np.ndarray,
        roi_enhanced: np.ndarray,
        det: Dict,
        motion_ratio: float,
    ) -> bool:
        total_pixels = max(roi_raw.shape[0] * roi_raw.shape[1], 1)
        hsv_raw = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2HSV)

        yellow_mask = cv2.inRange(hsv_raw, np.array([15, 80, 80]), np.array([45, 255, 255]))
        red_mask1 = cv2.inRange(hsv_raw, np.array([0, 70, 70]), np.array([15, 255, 255]))
        red_mask2 = cv2.inRange(hsv_raw, np.array([165, 70, 70]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        yellow_ratio = cv2.countNonZero(yellow_mask) / total_pixels
        red_ratio = cv2.countNonZero(red_mask) / total_pixels

        hit_count = 0
        reasons = []

        if yellow_ratio > 0.35 and red_ratio < 0.12:
            hit_count += 1
            reasons.append('yellow-high-red-low')

        s = hsv_raw[:, :, 1]
        v = hsv_raw[:, :, 2]
        hue_valid = (s > 60) & (v > 60)
        if np.count_nonzero(hue_valid) > 20:
            hue_std = float(np.std(hsv_raw[:, :, 0][hue_valid]))
        else:
            hue_std = 180.0

        if yellow_ratio > 0.20 and hue_std < 9.0:
            hit_count += 1
            reasons.append('narrow-hue')

        if total_pixels < self.fire_small_area_threshold and motion_ratio < max(self.fire_small_target_motion_min, 0.06):
            hit_count += 1
            reasons.append('small-stable')

        kernel = np.ones((3, 3), np.uint8)
        yellow_clean = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(yellow_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            c_area = cv2.contourArea(c)
            if c_area > 30:
                x, y, w, h = cv2.boundingRect(c)
                rect_area = max(w * h, 1)
                extent = float(c_area) / rect_area
                perimeter = max(cv2.arcLength(c, True), 1.0)
                complexity = (perimeter * perimeter) / (4.0 * np.pi * max(c_area, 1.0))
                if extent > 0.78 and complexity < 1.45:
                    hit_count += 1
                    reasons.append('regular-shape')

        if hit_count >= 2:
            self.logger.info(
                f"黄色小物体抑制命中: reasons={','.join(reasons)}, yellow={yellow_ratio:.2f}, red={red_ratio:.2f}, hue_std={hue_std:.2f}, motion={motion_ratio:.3f}, area={total_pixels}"
            )
            return True

        return False

    def _validate_fire(self, raw_frame: np.ndarray, enhanced_frame: np.ndarray, fg_mask: np.ndarray, det: Dict, skip_motion_check: bool = False) -> bool:
        """
        火焰多模态校验（含黄色小物体抑制与动态阈值）。
        """
        clipped = self._clip_det_box(det, raw_frame.shape)
        if clipped is None:
            self.logger.info("验证1/10失败: 检测框裁剪失败")
            return False

        xmin, ymin, xmax, ymax = clipped
        width, height = xmax - xmin, ymax - ymin
        total_pixels = width * height
        if total_pixels < 200:
            self.logger.info(f"验证2/10失败: ROI面积太小，area={total_pixels} < 200")
            return False

        roi_raw = raw_frame[ymin:ymax, xmin:xmax]
        roi_enhanced = enhanced_frame[ymin:ymax, xmin:xmax]
        if roi_raw.size == 0 or roi_enhanced.size == 0:
            self.logger.info("验证2/10失败: ROI为空")
            return False

        thresholds = self._get_dynamic_fire_thresholds(total_pixels)

        roi_fg = fg_mask[ymin:ymax, xmin:xmax]
        motion_ratio = cv2.countNonZero(roi_fg) / total_pixels

        ycrcb = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2YCrCb)
        skin_low = np.array([80, 135, 85])
        skin_high = np.array([200, 170, 125])
        skin_mask = cv2.inRange(ycrcb, skin_low, skin_high)
        skin_ratio = cv2.countNonZero(skin_mask) / total_pixels
        if skin_ratio > 0.45:
            self.logger.info(f"验证3/10失败: 肤色比例过高，skin_ratio={skin_ratio:.3f} > 0.45")
            return False

        if self.face_cascade and skin_ratio > 0.15:
            gray_roi_face = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray_roi_face, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
            if len(faces) > 0:
                self.logger.info(f"验证4/10失败: 检测到人脸，faces={len(faces)}")
                return False

        gray_roi = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_roi, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30, minLineLength=min(width, height) * 0.3, maxLineGap=10)
        if lines is not None and len(lines) >= 8:
            self.logger.info(f"验证5/10失败: 检测到过多直线，lines={len(lines)} >= 8")
            return False

        hsv = cv2.cvtColor(roi_enhanced, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.fire_color_low1, self.fire_color_high1)
        mask2 = cv2.inRange(hsv, self.fire_color_low2, self.fire_color_high2)
        mask3 = cv2.inRange(hsv, self.fire_color_low3, self.fire_color_high3)
        white_core_mask = cv2.inRange(hsv, np.array([0, 0, 220]), np.array([180, 60, 255]))
        fire_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)
        fire_mask = cv2.bitwise_or(fire_mask, white_core_mask)

        fire_ratio = cv2.countNonZero(fire_mask) / total_pixels
        if fire_ratio < thresholds['min_fire_ratio']:
            self.logger.info(
                f"验证6/10失败: 火焰颜色比例不足，fire_ratio={fire_ratio:.3f} < {thresholds['min_fire_ratio']:.3f}, scale={thresholds['scale']}"
            )
            return False

        hsv_raw = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2HSV)
        v_channel = hsv_raw[:, :, 2]
        highlight_mask = v_channel > 250
        highlight_ratio = np.count_nonzero(highlight_mask) / total_pixels

        avg_saturation = float(np.mean(hsv_raw[:, :, 1]))
        if avg_saturation < 35 and highlight_ratio < 0.1:
            self.logger.info(f"验证6/10失败: 平均饱和度不足，avg_saturation={avg_saturation:.2f} < 35 且 highlight_ratio={highlight_ratio:.3f} < 0.1")
            return False

        if self._is_yellow_object_false_alarm(roi_raw, roi_enhanced, det, motion_ratio):
            self.logger.info("验证7/10失败: 黄色小物体抑制命中")
            return False

        if highlight_ratio > 0.75:
            self.logger.info(f"验证8/10失败: 高亮区域过多，highlight_ratio={highlight_ratio:.3f} > 0.75")
            return False

        contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        complexity = 0.0
        c_area = 0.0
        c = None
        if contours:
            c = max(contours, key=cv2.contourArea)
            c_area = cv2.contourArea(c)
            if c_area > 50:
                perimeter = cv2.arcLength(c, True)
                complexity = (perimeter ** 2) / (4 * np.pi * c_area)

        if 0 < complexity < 1.3:
            self.logger.info(f"验证8/10失败: 轮廓复杂度不足，complexity={complexity:.2f} < 1.3")
            return False

        if c is not None:
            x, y, w, h = cv2.boundingRect(c)
            rect_area = w * h
            if rect_area > 0:
                extent = float(c_area) / rect_area
                if extent > 0.85 and det['conf'] < 0.80:
                    self.logger.info(f"验证8/10失败: 形状过于规则，extent={extent:.3f} > 0.85 且 conf={det['conf']:.3f} < 0.80")
                    return False

        v_std = float(np.std(v_channel))
        if v_std < thresholds['min_v_std']:
            self.logger.info(
                f"验证9/10失败: 亮度标准差不足，v_std={v_std:.2f} < {thresholds['min_v_std']:.2f}, scale={thresholds['scale']}"
            )
            return False

        if not skip_motion_check:
            if motion_ratio < thresholds['min_motion_ratio'] and complexity < 2.0:
                self.logger.info(
                    f"验证10/10失败: 运动比例不足，motion={motion_ratio:.3f} < {thresholds['min_motion_ratio']:.3f}, complexity={complexity:.2f}"
                )
                return False

        det['_box_area'] = total_pixels
        det['_motion_ratio'] = motion_ratio
        det['_fire_ratio'] = fire_ratio

        self.logger.info(
            f"火焰校验通过: scale={thresholds['scale']}, fire_ratio={fire_ratio:.3f}, motion={motion_ratio:.3f}, v_std={v_std:.2f}"
        )
        return True

    def _validate_smoke(self, raw_frame: np.ndarray, det: Dict) -> bool:
        """
        函数级注释：烟雾特征验证，专门过滤加湿器水汽、白色反光等
        水汽特征：饱和度极低，亮度极高，内部没有高频纹理（很平滑）
        火灾烟雾特征：通常夹杂灰/黑/黄色，有颗粒感（高频细节）
        """
        xmin, ymin, xmax, ymax = det['xmin'], det['ymin'], det['xmax'], det['ymax']
        width, height = xmax - xmin, ymax - ymin
        conf = det['conf']
        
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
        
        # [调整] 加湿器水汽通常非常白（亮度极高，饱和度接近0）
        # 之前的阈值 (V>210, S<20) 可能太严格，导致稍暗的水汽漏过
        # 现在的策略：如果是低置信度 (<0.75) 的检测，应用更严格的 HSV 过滤
        
        if conf < 0.75:
            # 低置信度：只要比较白 (V>160) 且饱和度低 (S<30)，就认为是水汽
            v_thresh = 160
            s_thresh = 30
        else:
            # 高置信度：要求非常白才过滤
            v_thresh = 200
            s_thresh = 20
            
        if avg_v > v_thresh and avg_s < s_thresh:
            self.logger.info(f"烟雾验证失败：疑似水汽/反光 (Conf={conf:.2f}, V={avg_v:.1f}>{v_thresh}, S={avg_s:.1f}<{s_thresh})")
            return False
            
        # ==========================================
        # 2. 纹理高频细节分析 (Laplacian 边缘检测方差)
        # ==========================================
        # 水汽内部非常平滑，边缘模糊；而浓烟内部有颗粒感，滚动时有明显的不规则纹理
        gray_roi = cv2.cvtColor(roi_raw, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_roi, cv2.CV_64F)
        variance = laplacian.var()
        
        # [调整] 根据置信度调整方差阈值
        var_thresh = 40 if conf < 0.75 else 25
        
        if variance < var_thresh:
            self.logger.info(f"烟雾验证失败：纹理太平滑 (方差 {variance:.1f} < {var_thresh})，疑似水汽")
            return False
            
        self.logger.info(f"烟雾验证通过: Conf={conf:.2f}, V={avg_v:.1f}, S={avg_s:.1f}, Var={variance:.1f}")
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
