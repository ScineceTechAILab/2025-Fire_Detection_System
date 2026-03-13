"""
类级注释：阿里云短信服务提供者
实现阿里云短信发送功能
"""
import json
import logging
from typing import List, Dict, Any, Optional

from alibabacloud_dysmsapi20170525.client import Client as DysmsApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysms_models
from alibabacloud_tea_util import models as util_models

from .base import SmsProvider


class AliyunSmsProvider(SmsProvider):
    """
    类级注释：阿里云短信服务提供者
    实现阿里云短信发送功能
    """

    def __init__(self, config: Dict[str, Any]):
        """
        函数级注释：初始化阿里云短信服务
        :param config: 配置字典，包含 access_key_id, access_key_secret, sign_name, template_code
        """
        self.logger = logging.getLogger("AliyunSMS")
        self.config = config
        
        self._access_key_id = config.get("access_key_id", "")
        self._access_key_secret = config.get("access_key_secret", "")
        self._sign_name = config.get("sms_sign_name", "")
        self._template_code = config.get("sms_template_code", "")
        
        self._client: Optional[DysmsApiClient] = None
        self.logger.info(f"阿里云短信提供者初始化完成")

    def get_provider_name(self) -> str:
        """
        函数级注释：获取服务提供商名称
        """
        return "aliyun"

    def is_available(self) -> bool:
        """
        函数级注释：检查服务是否可用
        """
        return all([
            self._access_key_id,
            self._access_key_secret,
            self._sign_name,
            self._template_code
        ])

    def _get_client(self) -> Optional[DysmsApiClient]:
        """
        函数级注释：获取或创建阿里云客户端
        """
        if self._client is None:
            if not self.is_available():
                self.logger.error("❌ 阿里云配置不完整")
                return None
            
            try:
                config = open_api_models.Config(
                    access_key_id=self._access_key_id,
                    access_key_secret=self._access_key_secret
                )
                config.endpoint = 'dysmsapi.aliyuncs.com'
                self._client = DysmsApiClient(config)
                self.logger.info("✅ 阿里云客户端初始化成功")
            except Exception as e:
                self.logger.exception(f"客户端初始化失败: {e}")
                return None
        return self._client

    def send_sms(
        self,
        phone_numbers: str | List[str],
        template_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        函数级注释：发送短信
        """
        client = self._get_client()
        if not client:
            return False

        if isinstance(phone_numbers, list):
            phone_numbers_str = ",".join(phone_numbers)
        else:
            phone_numbers_str = phone_numbers

        send_sms_request = dysms_models.SendSmsRequest(
            sign_name=self._sign_name,
            template_code=self._template_code,
            phone_numbers=phone_numbers_str,
            template_param=json.dumps(template_params) if template_params else "{}"
        )
        runtime = util_models.RuntimeOptions()

        try:
            self.logger.info(f"正在发送短信给: {phone_numbers_str} ...")
            resp = client.send_sms_with_options(send_sms_request, runtime)

            if resp.body.code == 'OK':
                self.logger.info(f"✅ 发送成功! ID: {resp.body.request_id}")
                return True
            else:
                self.logger.error(f"❌ 发送失败: {resp.body.message}")
                return False
        except Exception as e:
            self.logger.error(f"发送异常: {e}")
            return False
