"""
程序入口（支持配置热加载）
基于YOLOv8的视觉火灾检测系统主程序
"""
import time
import logging
import threading
import os
import cv2

# 初始化日志系统（必须在导入其他模块之前）
from utils.logging_config import setup_logging

# 使用绝对路径，确保在 Docker 中写入正确位置
log_dir = "/app/log" if os.path.exists("/app") else "log"
setup_logging(log_dir=log_dir, log_level=logging.INFO, retention_days=7)

from core.communication.communication import Communication
from core.communication.config_hot_loader import get_config_hot_loader
from core.yolo.detector import Detector

try:
    import torch
    import torch.nn as nn
    from ultralytics.nn.tasks import DetectionModel
    from ultralytics.nn.modules import Conv, Concat
    from ultralytics.nn.modules.head import Detect
    from ultralytics.nn.modules.block import C2f, Bottleneck, SPPF, DFL

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
    pass


class Main:
    """
    类级注释：主程序类
    """
    
    def __init__(self):
        self.logger = logging.getLogger("Main")
        
        # 初始化配置热加载器
        self.config_loader = get_config_hot_loader()
        
        self.last_alert_time = 0
        
        # 从配置获取 YOLO 参数，或使用默认值
        yolo_weights = self.config_loader.get_config('yolo_weights', 'core/yolo/weights/best.pt')
        yolo_device = self.config_loader.get_config('yolo_device', 'cuda')
        yolo_conf = self.config_loader.get_config('yolo_confidence', 0.8)
        
        self.detector = Detector(weights_path=yolo_weights, device=yolo_device, conf=yolo_conf)
        
        # 初始化通信模块
        self.comm = Communication()
        
        # 确保报警图片输出目录存在
        os.makedirs("output", exist_ok=True)
        
        self.logger.info("主程序初始化完成（支持配置热加载）")
    
    def _get_config(self):
        """
        函数级注释：获取最新配置
        """
        alert_interval = self.config_loader.get_config('alert_cooldown_seconds', 360)
        camera_index = self.config_loader.get_config('camera_index', 0)
        rtsp_url = self.config_loader.get_config('rtsp_url')
        detection_interval = self.config_loader.get_config('detection_interval', 5)
        consecutive_threshold = self.config_loader.get_config('consecutive_threshold', 12)
        
        return {
            'alert_interval': alert_interval,
            'camera_index': camera_index,
            'rtsp_url': rtsp_url,
            'detection_interval': detection_interval,
            'consecutive_threshold': consecutive_threshold
        }
    
    def run_detection_loop(self):
        """
        函数级注释：主检测循环
        处理视频流，连续检测到火灾后触发报警
        """
        config = self._get_config()
        
        # 优先使用 RTSP 流，如果未配置，则使用本地摄像头
        source = config['rtsp_url'] if config['rtsp_url'] else config['camera_index']
        cap = cv2.VideoCapture(source)
        
        # RTSP 流优化参数
        if config['rtsp_url']:
            # 设置缓冲区大小，减少延迟
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            # 设置读取超时（毫秒）
            cap.set(cv2.CAP_PROP_READ_TIMEOUT, 5000)
        
        if not cap.isOpened():
            self.logger.error(f"无法打开视频源: {source}")
            return
        
        self.logger.info(f"视频源打开成功: {source}")
        
        frame_count = 0
        consecutive_fire_detections = 0
        fire_state_active = False
        consecutive_read_errors = 0
        max_read_errors = 10
        
        while cap.isOpened():
            # 每次循环获取最新配置
            config = self._get_config()
            
            ret, frame = cap.read()
            if not ret:
                consecutive_read_errors += 1
                if consecutive_read_errors >= max_read_errors:
                    self.logger.error(f"连续 {consecutive_read_errors} 次无法读取视频帧，尝试重新连接...")
                    cap.release()
                    time.sleep(2)
                    cap = cv2.VideoCapture(source)
                    if config['rtsp_url']:
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
                        cap.set(cv2.CAP_PROP_READ_TIMEOUT, 5000)
                    if cap.isOpened():
                        self.logger.info("视频源重新连接成功")
                        consecutive_read_errors = 0
                    else:
                        self.logger.error("视频源重新连接失败，退出")
                        break
                else:
                    self.logger.warning(f"无法读取视频帧 ({consecutive_read_errors}/{max_read_errors}，继续尝试...")
                    time.sleep(0.5)
                    continue
            
            consecutive_read_errors = 0
            frame_count += 1
            annotated_frame = frame.copy()
            
            # 每隔 DETECTION_INTERVAL 帧进行一次识别
            if frame_count % config['detection_interval'] == 0:
                annotated_frame, detections = self.detector.detect_frame(frame, draw=True)
                
                # 检查是否检测到火灾
                is_fire_detected = any(det.get('cls_name', '').lower() == 'fire' for det in detections)
                
                if is_fire_detected:
                    consecutive_fire_detections += 1
                    if not fire_state_active:
                        fire_state_active = True
                        self.logger.warning(
                            f"检测到疑似火灾，开始连续计数 (阈值: {config['consecutive_threshold']})"
                        )
                    if consecutive_fire_detections >= config['consecutive_threshold']:
                        self.logger.warning(
                            f"疑似火灾连续次数达到阈值 ({consecutive_fire_detections}/{config['consecutive_threshold']})"
                        )
                else:
                    if consecutive_fire_detections > 0:
                        self.logger.info(f"疑似火灾消失，连续计数重置 (上次计数: {consecutive_fire_detections})")
                    consecutive_fire_detections = 0
                    fire_state_active = False
                
                # 检查是否满足报警条件
                if consecutive_fire_detections >= config['consecutive_threshold']:
                    current_time = time.time()
                    if current_time - self.last_alert_time > config['alert_interval']:
                        self.logger.warning(
                            f"触发报警: 连续 {config['consecutive_threshold']} 次检测到火灾"
                        )
                        self.last_alert_time = current_time
                        
                        # 保存带有检测框的图片用于报警
                        image_path = f"output/fire_alert_{int(current_time)}.jpg"
                        cv2.imwrite(image_path, annotated_frame)
                        self.logger.info(f"报警截图已保存: {image_path}")
                        
                        # 启动报警线程
                        alarm_thread = threading.Thread(
                            target=self.comm.run_fire_alarm_process_feishu,
                            args=(image_path,)
                        )
                        alarm_thread.start()
                        
                        # 报警后重置计数器
                        consecutive_fire_detections = 0
                        fire_state_active = False
                    else:
                        remaining = int(config['alert_interval'] - (current_time - self.last_alert_time))
                        if remaining < 0:
                            remaining = 0
                        self.logger.info(f"报警冷却中，剩余 {remaining}s，本次不重复触发")
            
            # 显示画面（仅在非 headless 模式下）
            if not os.getenv("HEADLESS"):
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
