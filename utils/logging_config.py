import logging
import sys
import os
import re
import queue
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from logging import FileHandler
from logging.handlers import QueueHandler, QueueListener


# 定义 UTC+8 时区（Asia/Shanghai）
TZ_UTC8 = timezone(timedelta(hours=8), name='Asia/Shanghai')


class DailyRotatingFileHandler(FileHandler):
    """
    类级注释：自定义的按天轮转文件处理器
    日志文件名格式：fire_detection_YYYY-MM-DD.log
    每天自动创建新的日志文件
    使用 UTC+8 时区
    """
    def __init__(self, log_dir, retention_days: int = 7):
        self.log_dir = Path(log_dir).absolute()
        self.log_dir.mkdir(exist_ok=True)
        print(f"[DEBUG] 日志目录: {self.log_dir}")  # 输出到控制台以便调试
        self.current_date = None
        self.current_file = None
        self.retention_days = retention_days
        
        # 初始化时打开今天的日志文件
        self._open_today_file()
        
        # 调用父类初始化
        super().__init__(self.current_file, mode='a', encoding='utf-8', delay=False)
        self._cleanup_old_logs()
    
    def _get_today_filename(self):
        """获取今天的日志文件名（使用 UTC+8 时区）"""
        today = datetime.now(TZ_UTC8).strftime("%Y-%m-%d")
        return self.log_dir / f"fire_detection_{today}.log"
    
    def _open_today_file(self):
        """打开今天的日志文件（使用 UTC+8 时区）"""
        today = datetime.now(TZ_UTC8).strftime("%Y-%m-%d")
        self.current_date = today
        self.current_file = str(self._get_today_filename())
    
    def _should_rollover(self):
        """检查是否需要轮转（日期是否变化，使用 UTC+8 时区）"""
        today = datetime.now(TZ_UTC8).strftime("%Y-%m-%d")
        return today != self.current_date
    
    def emit(self, record):
        """发送日志记录，如果日期变化则切换文件"""
        if self._should_rollover():
            self.doRollover()
        super().emit(record)
    
    def doRollover(self):
        """执行轮转：关闭旧文件，打开新日期的文件"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # 打开新日期的文件
        self._open_today_file()
        
        # 重新打开文件流
        self.baseFilename = self.current_file
        self.stream = self._open()
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        keep_days = int(self.retention_days) if self.retention_days else 7
        if keep_days <= 0:
            return

        today = datetime.now(TZ_UTC8).date()
        cutoff = today.toordinal() - keep_days

        pattern = re.compile(r"^fire_detection_(\d{4}-\d{2}-\d{2})\.log$")
        for p in self.log_dir.iterdir():
            if not p.is_file():
                continue
            m = pattern.match(p.name)
            if not m:
                continue
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except Exception:
                continue
            if file_date.toordinal() < cutoff:
                try:
                    p.unlink()
                except Exception:
                    pass


class UTC8Formatter(logging.Formatter):
    """
    类级注释：自定义日志格式化器，使用 UTC+8 时区
    """
    def formatTime(self, record, datefmt=None):
        """
        函数级注释：格式化时间为 UTC+8 时区
        """
        dt = datetime.fromtimestamp(record.created, TZ_UTC8)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


_LOG_QUEUE: queue.Queue | None = None
_LOG_LISTENER: QueueListener | None = None
_LOG_LOCK = threading.Lock()


def setup_logging(log_dir="log", log_level=logging.INFO, retention_days: int = 7):
    """
    函数级注释：配置全局日志系统，支持输出到文件和控制台
    日志文件按日期命名，格式：fire_detection_YYYY-MM-DD.log
    使用 UTC+8 时区
    
    :param log_dir: 日志文件存放目录
    :param log_level: 日志级别，默认为 INFO
    :param retention_days: 日志保留天数
    :return: None
    """
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    global _LOG_QUEUE, _LOG_LISTENER
    with _LOG_LOCK:
        if _LOG_LISTENER is not None:
            try:
                _LOG_LISTENER.stop()
            except Exception:
                pass
            _LOG_LISTENER = None
        _LOG_QUEUE = queue.Queue(-1)

        # 清除已有的处理器（避免重复添加）
        root_logger.handlers.clear()
    
    # 定义日志格式（使用 UTC+8 格式化器）
    formatter = UTC8Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器（输出到屏幕）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 文件处理器（按天轮转，每天自动创建新文件）
    file_handler = DailyRotatingFileHandler(log_dir, retention_days=retention_days)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    with _LOG_LOCK:
        qh = QueueHandler(_LOG_QUEUE)
        qh.setLevel(log_level)
        root_logger.addHandler(qh)

        _LOG_LISTENER = QueueListener(_LOG_QUEUE, console_handler, file_handler, respect_handler_level=True)
        _LOG_LISTENER.start()

    for noisy in [
        "ultralytics",
        "httpx",
        "urllib3",
        "requests",
        "PIL",
        "matplotlib",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
    
    return root_logger


def shutdown_logging():
    global _LOG_LISTENER
    with _LOG_LOCK:
        if _LOG_LISTENER is not None:
            try:
                _LOG_LISTENER.stop()
            except Exception:
                pass
            _LOG_LISTENER = None


def get_logger(name):
    """
    函数级注释：获取一个配置好的 Logger 对象
    
    :param name: 模块名称，比如 "Feishu", "YOLO", "Main"
    :return: logger 对象
    """
    return logging.getLogger(name)
