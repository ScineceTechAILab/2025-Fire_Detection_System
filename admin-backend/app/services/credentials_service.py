"""
类级注释：凭证配置管理服务
提供飞书、阿里云等第三方服务凭证的 CRUD 功能
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..core.storage import get_storage_manager


class CredentialsService:
    """
    类级注释：凭证配置管理服务
    """

    def __init__(self):
        self.storage = get_storage_manager()
        self.credentials_file = "credentials.json"
        self._init_default_credentials()

    def _init_default_credentials(self):
        """
        函数级注释：初始化默认凭证配置
        """
        default_credentials = {
            "sms_provider": "aliyun",
            "feishu": {
                "app_id": "",
                "app_secret": ""
            },
            "aliyun": {
                "access_key_id": "",
                "access_key_secret": "",
                "sms_sign_name": "",
                "sms_template_code": ""
            },
            "version": 1,
            "updated_at": datetime.now().isoformat()
        }

        credentials_data = self.storage.read(self.credentials_file)
        if not credentials_data:
            self.storage.write(self.credentials_file, default_credentials)

    def get_credentials(self) -> Dict[str, Any]:
        """
        函数级注释：获取所有凭证配置
        :return: 凭证字典
        """
        data = self.storage.read(self.credentials_file)
        return data or {}

    def get_feishu_credentials(self) -> Dict[str, str]:
        """
        函数级注释：获取飞书凭证
        :return: 飞书凭证字典
        """
        data = self.get_credentials()
        return data.get("feishu", {})

    def get_aliyun_credentials(self) -> Dict[str, str]:
        """
        函数级注释：获取阿里云凭证
        :return: 阿里云凭证字典
        """
        data = self.get_credentials()
        return data.get("aliyun", {})

    def get_sms_provider(self) -> str:
        """
        函数级注释：获取当前短信服务商
        :return: 短信服务商标识
        """
        data = self.get_credentials()
        return data.get("sms_provider", "aliyun")

    def update_sms_provider(self, provider: str) -> Dict[str, Any]:
        """
        函数级注释：更新短信服务商
        :param provider: 短信服务商标识，如 "aliyun", "tencent"
        :return: 更新后的凭证
        """
        data = self.get_credentials()
        data["sms_provider"] = provider
        data["version"] = data.get("version", 1) + 1
        data["updated_at"] = datetime.now().isoformat()
        self.storage.write(self.credentials_file, data)
        return data

    def update_feishu_credentials(self, app_id: str, app_secret: str) -> Dict[str, Any]:
        """
        函数级注释：更新飞书凭证
        :param app_id: 飞书应用 ID
        :param app_secret: 飞书应用密钥
        :return: 更新后的凭证
        """
        data = self.get_credentials()
        data["feishu"] = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        data["version"] = data.get("version", 1) + 1
        data["updated_at"] = datetime.now().isoformat()
        self.storage.write(self.credentials_file, data)
        return data

    def update_aliyun_credentials(
        self,
        access_key_id: str,
        access_key_secret: str,
        sms_sign_name: str,
        sms_template_code: str
    ) -> Dict[str, Any]:
        """
        函数级注释：更新阿里云凭证
        :param access_key_id: 阿里云 AccessKey ID
        :param access_key_secret: 阿里云 AccessKey Secret
        :param sms_sign_name: 短信签名
        :param sms_template_code: 短信模板代码
        :return: 更新后的凭证
        """
        data = self.get_credentials()
        data["aliyun"] = {
            "access_key_id": access_key_id,
            "access_key_secret": access_key_secret,
            "sms_sign_name": sms_sign_name,
            "sms_template_code": sms_template_code
        }
        data["version"] = data.get("version", 1) + 1
        data["updated_at"] = datetime.now().isoformat()
        self.storage.write(self.credentials_file, data)
        return data


_credentials_service: Optional[CredentialsService] = None


def get_credentials_service() -> CredentialsService:
    """
    函数级注释：获取凭证服务实例（单例模式）
    :return: CredentialsService 实例
    """
    global _credentials_service
    if _credentials_service is None:
        _credentials_service = CredentialsService()
    return _credentials_service
