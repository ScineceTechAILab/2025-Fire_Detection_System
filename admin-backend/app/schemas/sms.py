"""
类级注释：云短信管理数据验证模式
"""
from typing import List
from pydantic import BaseModel, Field
from .contact import Contact, ContactCreate, ContactUpdate


class SmsConfig(BaseModel):
    """
    类级注释：短信配置响应模式
    """
    contacts: List[Contact] = Field(default_factory=list, description="紧急联系人列表")
