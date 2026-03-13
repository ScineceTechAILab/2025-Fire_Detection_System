"""
类级注释：短信服务模块
提供短信发送功能的抽象接口和多厂商实现
"""
from .base import SmsProvider
from .aliyun_provider import AliyunSmsProvider
from .factory import SmsProviderFactory
from .manager import SmsManager, get_sms_manager

__all__ = [
    "SmsProvider",
    "AliyunSmsProvider",
    "SmsProviderFactory",
    "SmsManager",
    "get_sms_manager",
]

