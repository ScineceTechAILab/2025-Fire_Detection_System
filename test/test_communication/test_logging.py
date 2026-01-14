#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试日志功能的脚本
只发送短信和飞书管理员通知，不发送群聊消息
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
# 获取当前文件的目录，然后向上两级到达项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent  # test/test_communication -> test -> 项目根目录
sys.path.insert(0, str(project_root))

import logging
from utils.logging_config import setup_logging
from core.communication.communication import Communication

# 初始化日志系统（使用项目根目录的 log 文件夹）
log_dir = project_root / "log"
setup_logging(log_dir=str(log_dir), log_level=logging.INFO)

if __name__ == "__main__":
    logger = logging.getLogger("TestScript")
    logger.info("开始测试日志和通知功能...")
    
    # 创建通信实例
    comm = Communication()
    
    # 测试手机号（可以修改为你自己的手机号）
    test_phone = "18903690733"


    # 可选：如果有测试图片，可以传入图片路径
    # test_image = "test/test_imgs/test1.jpg"
    test_image = None
    
    # 执行测试
    comm.test_logging_notification(phone_number=test_phone, image_path=test_image)
    
    logger.info(f"测试脚本执行完成，请查看日志文件：{log_dir}/fire_detection_YYYY-MM-DD.log")
