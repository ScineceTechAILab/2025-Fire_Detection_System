"""
类级注释：云短信管理服务
提供短信配置的管理功能
"""
from typing import Optional
from ..core.storage import get_storage_manager
from .contact_service import ContactService


class SmsService:
    """
    类级注释：短信服务类
    """
    
    def __init__(self):
        """
        函数级注释：初始化短信服务
        """
        self.storage = get_storage_manager()
        self.contact_service = ContactService("sms")
    
    def _load_data(self) -> dict:
        """
        函数级注释：加载数据
        """
        data = self.storage.read("sms.json")
        if not data:
            return {"contacts": []}
        return data
    
    def get_config(self) -> dict:
        """
        函数级注释：获取短信配置
        """
        return self._load_data()
