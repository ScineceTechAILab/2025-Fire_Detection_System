"""
类级注释：联系人服务
提供联系人的增删改查操作
"""
from typing import List, Optional
from datetime import datetime
import uuid
from ..core.storage import get_storage_manager


class ContactService:
    """
    类级注释：联系人服务类
    """
    
    def __init__(self, storage_key: str):
        """
        函数级注释：初始化联系人服务
        :param storage_key: 存储键名（feishu 或 sms）
        """
        self.storage_key = storage_key
        self.storage = get_storage_manager()
    
    def _load_data(self) -> dict:
        """
        函数级注释：加载数据
        """
        data = self.storage.read(f"{self.storage_key}.json")
        if not data:
            return {"contacts": []}
        return data
    
    def _save_data(self, data: dict):
        """
        函数级注释：保存数据
        """
        self.storage.write(f"{self.storage_key}.json", data)
    
    def get_all(self) -> List[dict]:
        """
        函数级注释：获取所有联系人
        """
        data = self._load_data()
        return data.get("contacts", [])
    
    def get_by_id(self, contact_id: str) -> Optional[dict]:
        """
        函数级注释：根据ID获取联系人
        """
        contacts = self.get_all()
        for contact in contacts:
            if contact.get("id") == contact_id:
                return contact
        return None
    
    def create(self, contact_data: dict) -> dict:
        """
        函数级注释：创建联系人
        """
        data = self._load_data()
        contacts = data.get("contacts", [])
        
        now = datetime.utcnow().isoformat()
        new_contact = {
            "id": str(uuid.uuid4()),
            "name": contact_data["name"],
            "identity": contact_data["identity"],
            "phone": contact_data["phone"],
            "created_at": now,
            "updated_at": now
        }
        
        contacts.append(new_contact)
        data["contacts"] = contacts
        self._save_data(data)
        
        return new_contact
    
    def update(self, contact_id: str, update_data: dict) -> Optional[dict]:
        """
        函数级注释：更新联系人
        """
        data = self._load_data()
        contacts = data.get("contacts", [])
        
        updated = False
        for i, contact in enumerate(contacts):
            if contact.get("id") == contact_id:
                update_data["updated_at"] = datetime.utcnow().isoformat()
                contacts[i].update(update_data)
                updated = True
                break
        
        if updated:
            data["contacts"] = contacts
            self._save_data(data)
            return contacts[i]
        
        return None
    
    def delete(self, contact_id: str) -> bool:
        """
        函数级注释：删除联系人
        """
        data = self._load_data()
        contacts = data.get("contacts", [])
        original_len = len(contacts)
        
        contacts = [c for c in contacts if c.get("id") != contact_id]
        
        if len(contacts) != original_len:
            data["contacts"] = contacts
            self._save_data(data)
            return True
        
        return False
