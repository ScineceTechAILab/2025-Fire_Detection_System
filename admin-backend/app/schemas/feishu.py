"""
类级注释：飞书管理数据验证模式
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from .contact import Contact, ContactCreate, ContactUpdate


class FeishuGroupChatUpdate(BaseModel):
    """
    类级注释：飞书群聊ID更新模式
    """
    group_chat_id: str = Field(..., min_length=1, max_length=100, description="飞书群聊ID")


class FeishuConfig(BaseModel):
    """
    类级注释：飞书配置响应模式
    """
    group_chat_id: str = Field(..., description="飞书群聊ID")
    contacts: List[Contact] = Field(default_factory=list, description="紧急联系人列表")


class FeishuChatItem(BaseModel):
    chat_id: str = Field(..., description="群聊ID")
    name: str = Field(..., description="群聊名称")
