"""
类级注释：阿里云短信通知器（支持配置热加载）
提供发送短信通知的功能，使用配置热加载器动态获取配置
"""
import os
import json
import logging
from pathlib import Path

from alibabacloud_dysmsapi20170525.client import Client as DysmsApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysms_models
from alibabacloud_tea_util import models as util_models

from core.communication.config_hot_loader import get_config_hot_loader

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"


class AliyunNotifier:
    """
    类级注释：阿里云短信通知器
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AliyunSMS")
        
        # 初始化配置热加载器
        self.config_loader = get_config_hot_loader()
        
        # 客户端缓存
        self._client = None
        self._access_key_id = None
        self._access_key_secret = None
        
        # 注册配置变更回调
        self.config_loader.add_change_callback(self._on_config_change)
        
        self.logger.info("阿里云短信通知器初始化完成")
    
    def _on_config_change(self):
        """
        函数级注释：配置变更回调
        """
        self.logger.info("检测到配置变更，清空客户端缓存")
        self._client = None
    
    def _get_client(self):
        """
        函数级注释：获取或创建阿里云客户端
        """
        # 从热加载器获取最新配置
        access_key_id = self.config_loader.get_config('ali_access_key_id')
        access_key_secret = self.config_loader.get_config('ali_access_key_secret')
        
        # 检查配置是否变更
        if (access_key_id != self._access_key_id or 
            access_key_secret != self._access_key_secret or 
            self._client is None):
            
            if not access_key_id or not access_key_secret:
                self.logger.error("❌ 未配置阿里云 AccessKey")
                return None
            
            self.logger.info("重新初始化阿里云客户端...")
            self._access_key_id = access_key_id
            self._access_key_secret = access_key_secret
            
            config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret
            )
            config.endpoint = f'dysmsapi.aliyuncs.com'
            
            try:
                self._client = DysmsApiClient(config)
                self.logger.info("✅ 阿里云客户端初始化成功")
            except Exception as e:
                self.logger.exception(f"客户端初始化失败: {e}")
                return None
        
        return self._client
    
    def send_sms(self, phone_numbers, params=None):
        """
        函数级注释：发送短信
        :param phone_numbers: 字符串 "189xxx" 或 列表 ["189xxx"]
        :param params: 模板参数
        """
        client = self._get_client()
        if not client:
            return False
        
        # 获取最新配置
        sign_name = self.config_loader.get_config('ali_sms_sign_name')
        template_code = self.config_loader.get_config('ali_sms_template_code')
        
        if not sign_name or not template_code:
            self.logger.error("❌ 未配置短信签名或模板编码")
            return False
        
        if isinstance(phone_numbers, list):
            phone_numbers_str = ",".join(phone_numbers)
        else:
            phone_numbers_str = phone_numbers
        
        send_sms_request = dysms_models.SendSmsRequest(
            sign_name=sign_name,
            template_code=template_code,
            phone_numbers=phone_numbers_str,
            template_param=json.dumps(params) if params else "{}"
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
    
    def send_sms_to_all(self, params=None):
        """
        函数级注释：发送短信给所有配置的接收人
        """
        recipients = self.config_loader.get_sms_recipients()
        if not recipients:
            self.logger.error("❌ 没有加载到任何短信接收人")
            return False
        
        phone_numbers = [r['phone'] for r in recipients]
        return self.send_sms(phone_numbers, params)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    notifier = AliyunNotifier()
    
    # 测试获取接收人
    recipients = notifier.config_loader.get_sms_recipients()
    print(f"当前短信接收人: {recipients}")
