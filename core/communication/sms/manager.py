"""
类级注释：短信服务管理器
整合配置热加载、服务选择和短信发送功能
"""
import logging
from typing import List, Dict, Any, Optional

from core.communication.config_hot_loader import get_config_hot_loader
from .base import SmsProvider
from .factory import SmsProviderFactory


class SmsManager:
    """
    类级注释：短信服务管理器
    负责管理短信服务的初始化、配置热加载和短信发送
    """

    def __init__(self):
        self.logger = logging.getLogger("SmsManager")
        self.config_loader = get_config_hot_loader()
        
        self._provider: Optional[SmsProvider] = None
        self._provider_type: Optional[str] = None
        
        self._init_provider()
        self.config_loader.add_change_callback(self._on_config_change)
        
        self.logger.info("短信服务管理器初始化完成")

    def _init_provider(self):
        """
        函数级注释：初始化短信服务提供者
        """
        provider_type = self.config_loader.get_config('sms_provider', 'aliyun')
        
        aliyun_config = {
            'access_key_id': self.config_loader.get_config('ali_access_key_id', ''),
            'access_key_secret': self.config_loader.get_config('ali_access_key_secret', ''),
            'sms_sign_name': self.config_loader.get_config('ali_sms_sign_name', ''),
            'sms_template_code': self.config_loader.get_config('ali_sms_template_code', '')
        }
        
        config_map = {
            'aliyun': aliyun_config,
        }
        
        config = config_map.get(provider_type, {})
        
        self._provider = SmsProviderFactory.create_provider(provider_type, config)
        self._provider_type = provider_type
        
        if self._provider:
            self.logger.info(f"✅ 使用短信服务商: {provider_type}")
        else:
            self.logger.warning(f"⚠️  短信服务未正确配置")

    def _on_config_change(self):
        """
        函数级注释：配置变更回调
        """
        self.logger.info("检测到配置变更，重新初始化短信服务")
        self._init_provider()

    def send_sms(
        self,
        phone_numbers: str | List[str],
        template_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        函数级注释：发送短信
        :param phone_numbers: 手机号，支持字符串单个号码或列表多个号码
        :param template_params: 模板参数字典
        :return: 发送是否成功
        """
        if not self._provider:
            self.logger.error("❌ 短信服务未初始化")
            return False
        
        return self._provider.send_sms(phone_numbers, template_params)

    def send_sms_to_all(self, template_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        函数级注释：发送短信给所有配置的接收人
        :param template_params: 模板参数字典
        :return: 发送是否成功
        """
        recipients = self.config_loader.get_sms_recipients()
        if not recipients:
            self.logger.error("❌ 没有加载到任何短信接收人")
            return False
        
        phone_numbers = [r['phone'] for r in recipients]
        return self.send_sms(phone_numbers, template_params)

    def get_current_provider(self) -> Optional[str]:
        """
        函数级注释：获取当前使用的短信服务商
        :return: 服务商标识
        """
        return self._provider_type

    def is_available(self) -> bool:
        """
        函数级注释：检查短信服务是否可用
        :return: 是否可用
        """
        return self._provider is not None and self._provider.is_available()


_sms_manager: Optional[SmsManager] = None


def get_sms_manager() -> SmsManager:
    """
    函数级注释：获取短信管理器实例（单例模式）
    :return: SmsManager 实例
    """
    global _sms_manager
    if _sms_manager is None:
        _sms_manager = SmsManager()
    return _sms_manager
