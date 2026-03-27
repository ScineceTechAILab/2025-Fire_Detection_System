import os
import cv2
from ultralytics import YOLO

class FileManager:
    def __init__(self, record_folder="record"):
        self.record_folder = record_folder
        if not os.path.exists(self.record_folder):
            os.makedirs(self.record_folder)

    def get_next_filename(self, extension="jpg"):
        """获取文件夹中下一个可用的数字命名文件名"""
        extension = extension.lstrip('.')
        existing_files = []
        for f in os.listdir(self.record_folder):
            name, ext = os.path.splitext(f)
            if ext.lstrip('.').lower() == extension.lower() and name.isdigit():
                existing_files.append(int(name))
        next_number = max(existing_files, default=0) + 1
        return next_number, os.path.join(self.record_folder, f"{next_number}.{extension}")

    def save_frames(self, original_frame, annotated_frame, next_num):
        original_path = os.path.join(self.record_folder, f"{next_num}.jpg")
        annotated_path = os.path.join(self.record_folder, f"{next_num}_annotated.jpg")

        cv2.imwrite(original_path, original_frame)
        cv2.imwrite(annotated_path, annotated_frame)

        print(f"检测到目标，保存原始帧到 {original_path}")
        print(f"保存标注后的帧到 {annotated_path}")


class YoloDetector:
    def __init__(self, model_path, target_class="fire", conf_threshold=0.5):
        # 使用 ultralytics 直接加载模型，支持 .pt 权重文件
        self.model = YOLO(model_path)
        self.target_class = target_class
        self.conf_threshold = conf_threshold

    def infer(self, frame):
        """执行推理并返回结果对象"""
        # YOLO 内部完成前向传播与 NMS，输入的是由 OpenCV 处理好的 640x640 图像
        results = self.model(frame, imgsz=640, conf=self.conf_threshold, verbose=False)
        return results[0]

    def has_target(self, result):
        """判断推理结果中是否包含目标类别"""
        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            class_name = result.names[cls_id]
            if class_name == self.target_class:
                return True
        return False

    def annotate(self, result):
        """利用 YOLO 的内置方法生成带标注的图像，包含置信度"""
        return result.plot(conf=True, labels=True)


class VideoProcessor:
    def __init__(self, video_source, detector, file_manager):
        self.video_source = video_source
        self.detector = detector
        self.file_manager = file_manager

    def run(self):
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            print("无法打开视频流或摄像头，请检查视频源")
            return

        print("开始拉取视频流并进行推理...")
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取视频帧，可能视频源已断开")
                    break

                # 由 OpenCV 负责图像尺寸处理
                resized_frame = cv2.resize(frame, (640, 640))
                # YOLO 负责图像识别
                result = self.detector.infer(resized_frame)

                # 检查是否识别到了特定目标（ "fire"）
                if self.detector.has_target(result):
                    annotated_frame = self.detector.annotate(result)
                    next_num, _ = self.file_manager.get_next_filename("jpg")
                    self.file_manager.save_frames(frame, annotated_frame, next_num)
                else:
                    # 如果没有目标，使用原尺寸帧直接展示
                    annotated_frame = resized_frame

                cv2.imshow("YOLO Inference", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    MODEL_PATH = "best.pt"  #权重路径
    TARGET_CLASS = "fire"   #目标类别名称
    VIDEO_SOURCE = 0 #视频源地址，支持 RTSP 流或摄像头索引（如 0）

    file_manager = FileManager(record_folder="record")
    try:
        detector = YoloDetector(model_path=MODEL_PATH, target_class=TARGET_CLASS)
        app = VideoProcessor(video_source=VIDEO_SOURCE, detector=detector, file_manager=file_manager)
        app.run()
    except Exception as e:
        print(f"初始化模型或运行时发生错误: {e}")
