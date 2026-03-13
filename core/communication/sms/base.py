"""
类级注释：短信服务抽象基类
定义所有短信服务商必须实现的接口方法
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class SmsProvider(ABC):
    """
    类级注释：短信服务提供者抽象基类
    所有具体的短信服务商（阿里云、腾讯云等）都必须继承此类并实现抽象方法
    """

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """
        函数级注释：初始化短信服务提供者
        :param config: 配置字典，包含服务商所需的所有配置项
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        函数级注释：获取服务提供商名称
        :return: 服务商标识字符串，如 "aliyun", "tencent"
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        函数级注释：检查服务是否可用（配置是否完整）
        :return: 服务是否可用
        """
        pass
