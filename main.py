# 程序入口
import time
from core.communication.feishu import FeishuNotifier
from utils.logger import setup_logger
import threading
import os
import cv2
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
    CAMERA_INDEX = 0      # 本地摄像头索引，如果使用RTSP，此项无效
    RTSP_URL = None       # "rtsp://your_rtsp_stream_url"
    YOLO_WEIGHTS = "core/yolo/weights/best.pt" # YOLO 模型权重路径
    YOLO_DEVICE = "cuda"   # "cpu" 或 "cuda"

# 初始化通知器 (会自动加载 .env 里的管理员)
notifier = FeishuNotifier()


class Main:

    def __init__(self):
        self.logger = setup_logger("Main")
        self.last_alert_time = 0
        self.detector = Detector(weights_path=YOLO_WEIGHTS, device=YOLO_DEVICE, conf=0.5)
        # 确保报警图片输出目录存在
        os.makedirs("output", exist_ok=True)

    def run_fire_alarm_process_feishu(self, image_path):

        """
        【核心逻辑】全自动分级报警线程
        该函数会独立运行，不会阻塞摄像头画面
        """

        self.logger.info(f"🔥 [线程启动] 开始执行报警流程...")

        # 1. 记录开始时间
        start_time = time.time()

        # 2. 第一轮：发送 [短信 + App] 加急
        # urgent_type="sms" 意味着 App弹窗 + 短信 都会发
        self.logger.info("Step 1: 发送短信加急报警...")
        notifier.send_to_all_admins(
            title="实验室火灾警报",
            content="检测到明火！请在 3 分钟内回复【1】确认，否则将触发电话报警。",
            image_path=str(image_path),
            urgent_type="sms"
        )

        # 3. 准备轮询：获取所有管理员的 Chat ID
        # 我们只要收到任意一个管理员的回复，就停止升级
        admin_chat_ids = []
        for uid in notifier.admin_ids:
            cid = notifier.get_p2p_chat_id(uid)
            if cid:
                admin_chat_ids.append(cid)

        if not admin_chat_ids:
            self.logger.error("❌ 警告：无法获取管理员会话 ID，无法接收回复，流程中止")
            return

        # 4. 进入 3 分钟等待期 (轮询查岗)
        # 3分钟 = 180秒，每 5 秒查一次
        wait_seconds = 180
        is_confirmed = False

        self.logger.info(f"Step 2: 等待回复中 (限时 {wait_seconds} 秒)...")

        for i in range(wait_seconds // 5):
            # 遍历所有管理员的聊天记录
            for chat_id in admin_chat_ids:
                if notifier.check_user_reply(chat_id, start_time):
                    is_confirmed = True
                    break  # 跳出管理员循环

            if is_confirmed:
                break  # 跳出时间循环

            time.sleep(5)  # 休息5秒再查

        # 5. 判断结果
        if is_confirmed:
            self.logger.info("✅ 警报解除：管理员已确认收到。")
            # 可以发一条消息告诉大家：危机解除，有人处理了
            notifier.send_to_all_admins("警报解除", "管理员已响应，流程结束。", urgent_type="app")
        else:
            self.logger.info("⚠️ 超时未回复！")
            self.logger.info("Step 3: 升级为 [电话] 加急报警！")

            # 6. 第二轮：升级为 [电话] 加急
            # urgent_type="phone" 意味着 App + 短信 + 电话 都会轰炸
            notifier.send_to_all_admins(
                title="【紧急】火灾未响应",
                content="您未在规定时间内回复，系统发起自动电话通知！请立即处置！",
                image_path=str(image_path),
                urgent_type="phone"  # <--- 核心升级点
            )

# --- 在 YOLO 检测逻辑中调用 ---
# 假设你在 main loop 里检测到了火灾
# if is_fire_detected and (现在不在冷却时间内):
#     # 启动一个新线程去跑报警，这样 main loop 可以继续检测下一帧
#     t = threading.Thread(target=run_fire_alarm_process, args=("output/fire.jpg",))
#     t.start()
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
        CONSECUTIVE_THRESHOLD = 5 # 连续 5 次检测到目标才报警

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
                    consecutive_fire_detections = 0 # 未检测到则重置

                # 检查是否满足报警条件
                if consecutive_fire_detections >= CONSECUTIVE_THRESHOLD:
                    current_time = time.time()
                    if current_time - self.last_alert_time > ALERT_INTERVAL:
                        self.logger.warning(f"连续 {CONSECUTIVE_THRESHOLD} 次检测到火灾，准备触发报警！")
                        self.last_alert_time = current_time

                        # 保存带有检测框的图片用于报警
                        image_path = f"output/fire_alert_{int(current_time)}.jpg"
                        cv2.imwrite(image_path, annotated_frame)

                        # 启动报警线程
                        alarm_thread = threading.Thread(target=self.run_fire_alarm_process_feishu, args=(image_path,))
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