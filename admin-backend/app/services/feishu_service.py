"""
类级注释：飞书管理服务
提供飞书配置的管理功能
"""
from typing import Optional, Any, Dict, List
import time
import httpx

from ..core.storage import get_storage_manager
from ..core.config import get_settings
from .contact_service import ContactService


class FeishuService:
    """
    类级注释：飞书服务类
    """
    
    def __init__(self):
        """
        函数级注释：初始化飞书服务
        """
        self.storage = get_storage_manager()
        self.contact_service = ContactService("feishu")
        self._settings = get_settings()
        self._tenant_access_token: Optional[str] = None
        self._tenant_access_token_expire_at: float = 0.0
    
    def _load_data(self) -> dict:
        """
        函数级注释：加载数据
        """
        data = self.storage.read("feishu.json")
        if not data:
            return {"group_chat_id": "", "contacts": []}
        return data
    
    def _save_data(self, data: dict):
        """
        函数级注释：保存数据
        """
        self.storage.write("feishu.json", data)
    
    def get_config(self) -> dict:
        """
        函数级注释：获取飞书配置
        """
        return self._load_data()
    
    def update_group_chat_id(self, group_chat_id: str) -> dict:
        """
        函数级注释：更新群聊ID
        """
        data = self._load_data()
        data["group_chat_id"] = group_chat_id
        self._save_data(data)
        return data

    def _get_tenant_access_token(self) -> str:
        now = time.time()
        if self._tenant_access_token and now < (self._tenant_access_token_expire_at - 30):
            return self._tenant_access_token

        app_id = (self._settings.feishu_app_id or "").strip()
        app_secret = (self._settings.feishu_app_secret or "").strip()
        if not app_id or not app_secret:
            raise ValueError("未配置 feishu_app_id / feishu_app_secret")

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()

        if result.get("code") != 0:
            raise ValueError(f"获取飞书 tenant_access_token 失败: {result}")

        token = result.get("tenant_access_token")
        if not token:
            raise ValueError("获取飞书 tenant_access_token 失败: 响应缺少 tenant_access_token")

        expire = result.get("expire", 0) or 0
        self._tenant_access_token = token
        self._tenant_access_token_expire_at = now + float(expire)
        return token

    def list_bot_chats(self, page_size: int = 50, max_pages: int = 10) -> List[Dict[str, Any]]:
        token = self._get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://open.feishu.cn/open-apis/im/v1/chats"

        items: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        pages = 0

        while pages < max_pages:
            params: Dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                result = resp.json()

            if result.get("code") != 0:
                raise ValueError(f"获取飞书群聊列表失败: {result}")

            data = result.get("data") or {}
            for chat in (data.get("items") or []):
                items.append(
                    {
                        "chat_id": chat.get("chat_id", ""),
                        "name": chat.get("name") or "未命名群聊",
                    }
                )

            has_more = bool(data.get("has_more"))
            page_token = data.get("page_token")
            pages += 1

            if not has_more or not page_token:
                break

        uniq: Dict[str, Dict[str, Any]] = {}
        for it in items:
            chat_id = it.get("chat_id")
            if chat_id:
                uniq[chat_id] = it

        return list(uniq.values())
