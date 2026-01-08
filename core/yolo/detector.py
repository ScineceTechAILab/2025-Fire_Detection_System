import time
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO
import logging

# 可选依赖 torch，用于检测 CUDA 可用性与模型迁移
try:
    import torch
    _TORCH_AVAILABLE = True
except Exception:
    _TORCH_AVAILABLE = False

try:
    from config import CONFIDENCE_THRESHOLD, CAMERA_INDEX  # type: ignore
except Exception:
    CONFIDENCE_THRESHOLD = 0.5
    CAMERA_INDEX = 0

from utils.logger import setup_logger


class Detector:
    """
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
        self.logger = setup_logger("Detector")
        self.weights_path = weights_path
        self.conf = float(conf) if conf is not None else CONFIDENCE_THRESHOLD
        self.device = device
        self.classes = classes
        self.imgsz = imgsz

        self.logger.info(f"初始化 Detector: weights={self.weights_path}, conf={self.conf}, device={self.device}")
        self.model = self._load_model()

    def _load_model(self) -> YOLO:
        try:
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
                    detections.append(det)
                    if draw:
                        self._draw_box(annotated, det)

        if return_time:
            return annotated, detections, elapsed
        return annotated, detections

    def _draw_box(self, img: np.ndarray, det: Dict):
        color = (0, 0, 255)
        cv2.rectangle(img, (det["xmin"], det["ymin"]), (det["xmax"], det["ymax"]), color, 2)
        label = f'{det["cls_name"]} {det["conf"]:.2f}'
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y0 = max(det["ymin"], h + 6)
        cv2.rectangle(img, (det["xmin"], y0 - h - 6), (det["xmin"] + w, y0), color, -1)
        cv2.putText(img, label, (det["xmin"], y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
