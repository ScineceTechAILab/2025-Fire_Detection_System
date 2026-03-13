"""
类级注释：短信服务工厂
根据配置动态创建对应的短信服务提供者实例
"""
import logging
from typing import Dict, Any, Optional, Type

from .base import SmsProvider
from .aliyun_provider import AliyunSmsProvider


class SmsProviderFactory:
    """
    类级注释：短信服务提供者工厂
    负责根据配置创建对应的短信服务实例
    """

    _providers: Dict[str, Type[SmsProvider]] = {
        "aliyun": AliyunSmsProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[SmsProvider]):
        """
        函数级注释：注册新的短信服务提供者
        :param name: 服务商标识
        :param provider_class: 提供者类
        """
        cls._providers[name] = provider_class
        logging.getLogger("SmsFactory").info(f"注册短信服务商: {name}")

    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[SmsProvider]:
        """
        函数级注释：创建短信服务提供者实例
        :param provider_type: 服务商标识，如 "aliyun"
        :param config: 配置字典
        :return: 短信服务提供者实例，失败返回 None
        """
        logger = logging.getLogger("SmsFactory")
        
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            logger.error(f"❌ 不支持的短信服务商: {provider_type}")
            logger.error(f"   支持的服务商: {list(cls._providers.keys())}")
            return None
        
        try:
            provider = provider_class(config)
            if provider.is_available():
                logger.info(f"✅ 创建短信服务成功: {provider_type}")
                return provider
            else:
                logger.error(f"❌ 配置不完整: {provider_type}")
                return None
        except Exception as e:
            logger.exception(f"创建短信服务失败: {e}")
            return None

    @classmethod
    def get_supported_providers(cls) -> list:
        """
        函数级注释：获取所有支持的服务商列表
        :return: 服务商名称列表
        """
        return list(cls._providers.keys())
