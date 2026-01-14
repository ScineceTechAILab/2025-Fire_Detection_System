# utils/logging_config.py
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from logging import FileHandler


class DailyRotatingFileHandler(FileHandler):
    """
    自定义的按天轮转文件处理器
    日志文件名格式：fire_detection_YYYY-MM-DD.log
    每天自动创建新的日志文件
    """
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_date = None
        self.current_file = None
        
        # 初始化时打开今天的日志文件
        self._open_today_file()
        
        # 调用父类初始化
        super().__init__(self.current_file, mode='a', encoding='utf-8', delay=False)
    
    def _get_today_filename(self):
        """获取今天的日志文件名"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"fire_detection_{today}.log"
    
    def _open_today_file(self):
        """打开今天的日志文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.current_date = today
        self.current_file = str(self._get_today_filename())
    
    def _should_rollover(self):
        """检查是否需要轮转（日期是否变化）"""
        today = datetime.now().strftime("%Y-%m-%d")
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


def setup_logging(log_dir="log", log_level=logging.INFO):
    """
    配置全局日志系统，支持输出到文件和控制台
    日志文件按日期命名，格式：fire_detection_YYYY-MM-DD.log
    :param log_dir: 日志文件存放目录
    :param log_level: 日志级别，默认为 INFO
    :return: None
    """
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的处理器（避免重复添加）
    root_logger.handlers.clear()
    
    # 定义日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器（输出到屏幕）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（按天轮转，每天自动创建新文件）
    file_handler = DailyRotatingFileHandler(log_dir)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name):
    """
    获取一个配置好的 Logger 对象
    :param name: 模块名称，比如 "Feishu", "YOLO", "Main"
    :return: logger 对象
    """
    return logging.getLogger(name)
