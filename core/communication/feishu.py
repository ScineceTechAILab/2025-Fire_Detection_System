"""
类级注释：飞书通知器（支持配置热加载）
提供发送飞书通知、加急、获取用户信息等功能，使用配置热加载器动态获取配置
"""
import requests
import json
import time
import os
import logging
from pathlib import Path

from core.communication.config_hot_loader import get_config_hot_loader

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"


class FeishuNotifier:
    """
    类级注释：飞书通知器
    """
    
    def __init__(self, webhook_url=None):
        self.logger = logging.getLogger("Feishu")
        
        # 初始化配置热加载器
        self.config_loader = get_config_hot_loader()
        
        # 注册配置变更回调
        self.config_loader.add_change_callback(self._on_config_change)
        
        # 缓存
        self._tenant_token = None
        self._token_expire_time = 0
        self._admin_ids = []
        self._admin_load_time = 0
        
        self.logger.info("飞书通知器初始化完成")
    
    def _on_config_change(self):
        """
        函数级注释：配置变更回调
        """
        self.logger.info("检测到配置变更，清空缓存")
        self._tenant_token = None
        self._admin_ids = []
        self._admin_load_time = 0
    
    def _get_tenant_access_token(self):
        """
        函数级注释：获取飞书租户访问令牌（带缓存）
        """
        now = time.time()
        
        # 检查缓存是否有效
        if self._tenant_token and now < self._token_expire_time:
            return self._tenant_token
        
        # 获取最新配置
        app_id = self.config_loader.get_config('feishu_app_id')
        app_secret = self.config_loader.get_config('feishu_app_secret')
        
        if not app_id or not app_secret:
            self.logger.error("未配置飞书 App ID 或 App Secret")
            return None
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {"app_id": app_id, "app_secret": app_secret}
        
        try:
            resp = requests.post(url, json=data, proxies={"http": None, "https": None})
            if resp.json().get("code") == 0:
                self._tenant_token = resp.json().get("tenant_access_token")
                # 提前 5 分钟过期，避免临界问题
                self._token_expire_time = now + resp.json().get("expire", 7200) - 300
                self.logger.info("获取飞书 Token 成功")
                return self._tenant_token
            self.logger.error(f"Token 获取失败: {resp.text}")
            return None
        except Exception as e:
            self.logger.exception(f"获取 Token 异常: {e}")
            return None
    
    def get_open_id_by_mobile(self, mobile):
        """
        函数级注释：通过手机号获取用户 open_id
        """
        self.logger.debug("通过手机号获取用户 open_id")
        if not mobile.startswith("+"): 
            mobile = f"+{mobile}"
        
        token = self._get_tenant_access_token()
        if not token: 
            return None
        
        url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = requests.post(
                url, headers=headers, 
                params={"user_id_type": "open_id"}, 
                json={"mobiles": [mobile]},
                proxies={"http": None, "https": None}
            )
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("user_list"):
                return data.get("data").get("user_list")[0].get("user_id")
            return None
        except Exception as e:
            self.logger.error(f"通过手机号获取用户 open_id 异常: {mobile}")
            return None
    
    def get_admin_ids(self, force_refresh: bool = False):
        """
        函数级注释：获取管理员 open_id 列表
        :param force_refresh: 是否强制刷新
        """
        now = time.time()
        
        # 检查是否需要刷新（5分钟缓存）
        if not force_refresh and self._admin_ids and (now - self._admin_load_time) < 300:
            return self._admin_ids
        
        # 从配置获取接收人
        recipients = self.config_loader.get_feishu_recipients()
        
        if not recipients:
            self.logger.warning("未配置飞书接收人")
            return []
        
        self.logger.info("开始加载飞书管理员列表")
        admin_ids = []
        
        for recipient in recipients:
            feishu_open_id = recipient.get('feishu_open_id')
            name = recipient.get('name', '未知')
            phone = recipient.get('phone')
            
            if feishu_open_id:
                if feishu_open_id not in admin_ids:
                    admin_ids.append(feishu_open_id)
            elif phone:
                self.logger.debug(f"{name} 无 open_id，尝试通过手机号获取")
                open_id = self.get_open_id_by_mobile(phone)
                if open_id:
                    if open_id not in admin_ids:
                        admin_ids.append(open_id)
                else:
                    self.logger.warning(f"无法获取 {name} 的飞书 open_id")
            else:
                self.logger.warning(f"接收人 {name} 未配置飞书 open_id 和手机号")
        
        self._admin_ids = admin_ids
        self._admin_load_time = now
        self.logger.info(f"飞书管理员加载完成，共 {len(admin_ids)} 人")
        return admin_ids
    
    @property
    def admin_ids(self):
        """
        属性：获取管理员 open_id 列表
        """
        return self.get_admin_ids()
    
    def upload_image(self, image_path):
        """
        函数级注释：上传图片到飞书
        """
        token = self._get_tenant_access_token()
        if not token: 
            return None
        
        url = "https://open.feishu.cn/open-apis/im/v1/images"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            files = {'image_type': (None, 'message'), 'image': image_data}
            resp = requests.post(
                url, headers=headers, files=files, 
                proxies={"http": None, "https": None}
            )
            if resp.json().get("code") == 0:
                return resp.json().get("data", {}).get("image_key")
            return None
        except Exception as e:
            self.logger.exception(f"上传图片异常: {e}")
            return None
    
    def buzz_message(self, message_id, user_id_list, urgent_type="sms"):
        """
        函数级注释：对消息进行加急
        """
        token = self._get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/urgent_{urgent_type}"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"user_id_list": user_id_list, "urgent_type": urgent_type}
        
        try:
            resp = requests.patch(
                url, headers=headers, 
                params={"user_id_type": "open_id"}, 
                json=data,
                proxies={"http": None, "https": None}
            )
            if resp.json().get("code") == 0:
                self.logger.info(f"[{urgent_type}] 加急发送成功")
                return True
            else:
                self.logger.error(f"加急失败: {resp.json()}")
                return False
        except Exception as e:
            self.logger.exception(f"加急异常: {e}")
            return False
    
    def send_card_to_group(self, title, content, image_path=None):
        """
        函数级注释：发送卡片到群聊
        """
        group_chat_id = self.config_loader.get_config('feishu_group_chat_id')
        keyword = self.config_loader.get_config('feishu_keyword', '')
        
        if not group_chat_id:
            self.logger.error("❌ 未配置飞书群聊ID")
            return None
        
        token = self._get_tenant_access_token()
        if not token: 
            return None
        
        image_key = None
        if image_path:
            image_key = self.upload_image(image_path)
        
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        final_title = f"【{keyword}】{title}" if keyword else title
        
        elements = [
            {"tag": "div", "text": {"content": f"**时间**: {time_str}\n**详情**: {content}", "tag": "lark_md"}},
        ]
        if image_key:
            elements.append({"tag": "img", "img_key": image_key, "alt": {"content": "现场图", "tag": "plain_text"}})
        
        elements.append({"tag": "hr"})
        elements.append({"tag": "div",
                         "text": {"content": "🔴 **所有成员请注意**：\n收到请在群内回复 **1** 或 **收到** 以解除警报。",
                                  "tag": "lark_md"}})
        
        card_content = {
            "header": {"template": "red", "title": {"content": f"🔥 {final_title}", "tag": "plain_text"}},
            "elements": elements
        }
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"receive_id_type": "chat_id"}
        body = {
            "receive_id": group_chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        try:
            resp = requests.post(
                url, headers=headers, params=params, json=body, 
                proxies={"http": None, "https": None}
            )
            res = resp.json()
            if res.get("code") == 0:
                msg_id = res.get("data", {}).get("message_id")
                self.logger.info(f"群消息发送成功 ID: {msg_id}")
                return msg_id
            else:
                self.logger.error(f"群发失败: {res}")
                return None
        except Exception as e:
            self.logger.exception(f"发送异常: {e}")
            return None
    
    def check_chat_reply(self, start_time_ts):
        """
        函数级注释：检查群里有没有人回复确认
        """
        group_chat_id = self.config_loader.get_config('feishu_group_chat_id')
        
        if not group_chat_id: 
            return False
        
        token = self._get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        
        safe_start_time = str(int(start_time_ts - 10))
        
        params = {
            "container_id_type": "chat",
            "container_id": group_chat_id,
            "start_time": safe_start_time,
            "page_size": 50
        }
        
        try:
            resp = requests.get(
                url, headers=headers, params=params, 
                proxies={"http": None, "https": None}
            )
            data = resp.json()
            
            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])
                
                for msg in items:
                    content_json = msg.get("body", {}).get("content", "{}")
                    content_dict = json.loads(content_json)
                    text = content_dict.get("text", "").strip()
                    sender_type = msg.get("sender", {}).get("sender_type")
                    
                    if sender_type != "user":
                        continue
                    
                    if text in ["1", "收到", "ok", "OK", "确认", "知道了"]:
                        self.logger.info(f"✅ 检测到确认回复: {text}")
                        return True
            else:
                self.logger.warning(f"轮询接口报错: {data}")
            
            return False
        except Exception as e:
            self.logger.exception(f"轮询异常: {e}")
            return False
    
    def send_card_to_user(self, user_open_id, title, content, image_path=None):
        """
        函数级注释：发送卡片消息给单个用户
        """
        if not user_open_id:
            self.logger.error("❌ 未提供用户 open_id")
            return None
        
        token = self._get_tenant_access_token()
        if not token:
            return None
        
        image_key = None
        if image_path:
            image_key = self.upload_image(image_path)
        
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        keyword = self.config_loader.get_config('feishu_keyword', '')
        final_title = f"【{keyword}】{title}" if keyword else title
        
        elements = [
            {"tag": "div", "text": {"content": f"**时间**: {time_str}\n**详情**: {content}", "tag": "lark_md"}},
        ]
        if image_key:
            elements.append({"tag": "img", "img_key": image_key, "alt": {"content": "现场图", "tag": "plain_text"}})
        
        card_content = {
            "header": {"template": "red", "title": {"content": f"🔥 {final_title}", "tag": "plain_text"}},
            "elements": elements
        }
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"receive_id_type": "open_id"}
        body = {
            "receive_id": user_open_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        try:
            resp = requests.post(
                url, headers=headers, params=params, json=body, 
                proxies={"http": None, "https": None}
            )
            res = resp.json()
            if res.get("code") == 0:
                msg_id = res.get("data", {}).get("message_id")
                self.logger.info(f"用户消息发送成功 ID: {msg_id}")
                return msg_id
            else:
                self.logger.error(f"用户消息发送失败: {res}")
                return None
        except Exception as e:
            self.logger.exception(f"发送用户消息异常: {e}")
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    notifier = FeishuNotifier()
    
    print("飞书通知器初始化完成")
    print(f"管理员列表: {notifier.admin_ids}")
