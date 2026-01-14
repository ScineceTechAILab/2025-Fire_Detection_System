import os
import sys
import json
import time
from pathlib import Path
# 引入 dotenv_values 用于直接读取文件
from dotenv import load_dotenv, dotenv_values

# 引入阿里云 SDK
from alibabacloud_dysmsapi20170525.client import Client as DysmsApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysms_models
from alibabacloud_tea_util import models as util_models

# 强制关闭代理
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

# 引入日志
import logging


class AliyunNotifier:
    def __init__(self):
        self.logger = logging.getLogger("AliyunSMS")

        # 1. 确定 .env 路径
        current_dir = Path(__file__).resolve().parent
        self.project_root = current_dir.parent.parent
        self.env_path = self.project_root / ".env"

        # 2. 加载环境变量
        self._load_env()

        # 3. 读取配置
        self.access_key_id = os.getenv("ALI_ACCESS_KEY_ID")
        self.access_key_secret = os.getenv("ALI_ACCESS_KEY_SECRET")
        self.sign_name = os.getenv("ALI_SMS_SIGN_NAME")
        self.template_code = os.getenv("ALI_SMS_TEMPLATE_CODE")

        # 4. 初始化客户端
        self.client = self._create_client()

        # 5. 【新增】自动加载短信接收人列表
        self.phone_numbers = []
        self._auto_load_phone_numbers()

    def _load_env(self):
        if self.env_path.exists():
            load_dotenv(dotenv_path=self.env_path, override=True)
        else:
            self.logger.warning("未找到 .env 文件")

    def _create_client(self):
        if not self.access_key_id or not self.access_key_secret:
            self.logger.error("❌ 未配置阿里云 AccessKey")
            return None
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret
        )
        config.endpoint = f'dysmsapi.aliyuncs.com'
        try:
            return DysmsApiClient(config)
        except Exception:
            self.logger.exception("客户端初始化失败")
            return None

    def _auto_load_phone_numbers(self):
        """
        【核心方法】自动扫描 .env 中以 sms_phone 开头的配置
        """
        if not self.env_path.exists():
            return

        # 直接读取文件，不依赖系统缓存
        env_config = dotenv_values(self.env_path)

        count = 0
        self.logger.info("正在加载短信接收人...")

        for key, value in env_config.items():
            # 只要 key 是以 sms_phone 开头的
            if key.startswith("sms_phone") and value:
                phone = value.strip()
                # 简单去重
                if phone not in self.phone_numbers:
                    self.phone_numbers.append(phone)
                    count += 1
                    self.logger.info(f"✅ 已加载接收人: {key} -> {phone}")

        self.logger.info(f"短信列表加载完毕，共 {count} 人")

    def send_sms(self, phone_numbers, params=None):
        """
        底层发送方法
        :param phone_numbers: 字符串 "189xxx" 或 列表 ["189xxx"]
        """
        if not self.client: return False

        # 处理列表转字符串
        if isinstance(phone_numbers, list):
            phone_numbers_str = ",".join(phone_numbers)
        else:
            phone_numbers_str = phone_numbers

        # 构造请求
        send_sms_request = dysms_models.SendSmsRequest(
            sign_name=self.sign_name,
            template_code=self.template_code,
            phone_numbers=phone_numbers_str,
            template_param=json.dumps(params) if params else "{}"
        )
        runtime = util_models.RuntimeOptions()

        try:
            self.logger.info(f"正在发送短信给: {phone_numbers_str} ...")
            resp = self.client.send_sms_with_options(send_sms_request, runtime)

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
        【便捷方法】一键给 .env 里配置的所有人发短信
        """
        if not self.phone_numbers:
            self.logger.error("❌ 没有加载到任何手机号，无法群发")
            return False

        return self.send_sms(self.phone_numbers, params)


# --- 测试代码 ---
if __name__ == "__main__":
    notifier = AliyunNotifier()

    # 打印看下加载结果
    print(f"当前接收列表: {notifier.phone_numbers}")

    # 测试群发
    # 假设你的模板变量是 ${time}
    # params = {"time": time.strftime("%H:%M")}
    # notifier.send_sms_to_all(params)
