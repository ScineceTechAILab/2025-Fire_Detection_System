# 程序入口
import time
import logging
import threading
import os
import cv2

# 初始化日志系统（必须在导入其他模块之前）
from utils.logging_config import setup_logging

setup_logging(log_dir="log", log_level=logging.INFO)

from core.communication.communication import Communication
from core.yolo.detector import Detector

try:
    import torch
    import torch.nn as nn
    from ultralytics.nn.tasks import DetectionModel
    from ultralytics.nn.modules import Conv, Concat
    from ultralytics.nn.modules.head import Detect
    from ultralytics.nn.modules.block import C2f, Bottleneck, SPPF, DFL

    # 将 YOLOv8 模型所需的常见类标记为安全，以兼容 torch.load 的新安全策略
    torch.serialization.add_safe_globals([
        DetectionModel,
        Conv,
        C2f,
        Bottleneck,
        SPPF,
        DFL,
        Detect,
        Concat,
        nn.Sequential,
        nn.Conv2d,
        nn.BatchNorm2d,
        nn.SiLU,
        nn.ModuleList,
        nn.Upsample,
        nn.MaxPool2d,
    ])
except (ImportError, AttributeError):
    # 如果 torch 或 ultralytics 未安装，或 torch 版本较旧，则忽略
    pass

try:
    from config import ALERT_INTERVAL, CAMERA_INDEX, RTSP_URL, YOLO_WEIGHTS, YOLO_DEVICE  # type: ignore
except Exception:
    # --- 如果 config.py 不存在，则使用以下默认值 ---
    ALERT_INTERVAL = 60  # 默认报警冷却时间（秒）
    CAMERA_INDEX = 0  # 本地摄像头索引，如果使用RTSP，此项无效
    RTSP_URL = None  # "rtsp://your_rtsp_stream_url"
    YOLO_WEIGHTS = "core/yolo/weights/best.pt"  # YOLO 模型权重路径
    YOLO_DEVICE = "cuda"  # "cpu" 或 "cuda"


class Main:

    def __init__(self):
        self.logger = logging.getLogger("Main")
        self.last_alert_time = 0
        self.detector = Detector(weights_path=YOLO_WEIGHTS, device=YOLO_DEVICE, conf=0.5)
        # 初始化通信模块
        self.comm = Communication()
        # 确保报警图片输出目录存在
        os.makedirs("output", exist_ok=True)

    def run_detection_loop(self):
        """
        主检测循环：处理视频流，连续检测到火灾后触发报警。
        """
        # 优先使用 RTSP 流，如果未配置，则使用本地摄像头
        source = RTSP_URL if RTSP_URL else CAMERA_INDEX
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            self.logger.error(f"无法打开视频源: {source}")
            return

        self.logger.info(f"视频源打开成功: {source}")

        frame_count = 0
        consecutive_fire_detections = 0
        DETECTION_INTERVAL = 5  # 每 5 帧检测一次
        CONSECUTIVE_THRESHOLD = 5  # 连续 5 次检测到目标才报警

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                self.logger.warning("无法读取视频帧，可能已结束。")
                break

            frame_count += 1
            annotated_frame = frame.copy()

            # 每隔 DETECTION_INTERVAL 帧进行一次识别
            if frame_count % DETECTION_INTERVAL == 0:
                annotated_frame, detections = self.detector.detect_frame(frame, draw=True)

                # 检查是否检测到火灾 (火灾类别名为 'fire')
                is_fire_detected = any(det.get('cls_name', '').lower() == 'fire' for det in detections)

                if is_fire_detected:
                    consecutive_fire_detections += 1
                    self.logger.info(f"检测到火灾! (连续次数: {consecutive_fire_detections}/{CONSECUTIVE_THRESHOLD})")
                else:
                    if consecutive_fire_detections > 0:
                        self.logger.info("火灾消失，重置计数器。")
                    consecutive_fire_detections = 0  # 未检测到则重置

                # 检查是否满足报警条件
                if consecutive_fire_detections >= CONSECUTIVE_THRESHOLD:
                    current_time = time.time()
                    if current_time - self.last_alert_time > ALERT_INTERVAL:
                        self.logger.warning(f"连续 {CONSECUTIVE_THRESHOLD} 次检测到火灾，准备触发报警！")
                        self.last_alert_time = current_time

                        # 保存带有检测框的图片用于报警
                        image_path = f"output/fire_alert_{int(current_time)}.jpg"
                        cv2.imwrite(image_path, annotated_frame)

                        # 启动报警线程，调用 Communication 类的报警方法
                        alarm_thread = threading.Thread(
                            target=self.comm.run_fire_alarm_process_feishu,
                            args=(image_path,)
                        )
                        alarm_thread.start()

                        # 报警后重置计数器，避免在冷却时间内重复启动线程
                        consecutive_fire_detections = 0
                    else:
                        self.logger.info("报警冷却中，本次不重复触发。")

            # 显示画面
            cv2.imshow("Fire Detection", annotated_frame)

            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        self.logger.info("程序已退出。")


if __name__ == "__main__":
    main_app = Main()
    main_app.run_detection_loop()
