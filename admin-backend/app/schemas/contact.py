"""
类级注释：联系人数据验证模式
定义联系人的数据结构和校验规则
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re
import uuid
from datetime import datetime


class ContactBase(BaseModel):
    """
    类级注释：联系人基础模式
    """
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    identity: str = Field(..., min_length=1, max_length=50, description="身份")
    phone: str = Field(..., description="手机号")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """
        函数级注释：验证手机号格式
        前端输入后自动补全国家码 +86
        """
        if not v:
            raise ValueError('手机号不能为空')
        
        # 移除空格和分隔符
        phone = re.sub(r'[\s\-]', '', v)
        
        # 如果没有国家码，自动补全 +86
        if not phone.startswith('+'):
            if phone.startswith('86'):
                phone = '+' + phone
            else:
                phone = '+86' + phone
        
        # 验证格式：+86 后面跟 11 位数字，以 1 开头
        if not re.match(r'^\+861[3-9]\d{9}$', phone):
            raise ValueError('手机号格式不正确，应为 11 位有效手机号')
        
        return phone


class ContactCreate(ContactBase):
    """
    类级注释：联系人创建模式
    """
    pass


class ContactUpdate(BaseModel):
    """
    类级注释：联系人更新模式
    """
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="姓名")
    identity: Optional[str] = Field(None, min_length=1, max_length=50, description="身份")
    phone: Optional[str] = Field(None, description="手机号")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """
        函数级注释：验证手机号格式
        """
        if v is None:
            return v
        
        phone = re.sub(r'[\s\-]', '', v)
        
        if not phone.startswith('+'):
            if phone.startswith('86'):
                phone = '+' + phone
            else:
                phone = '+86' + phone
        
        if not re.match(r'^\+861[3-9]\d{9}$', phone):
            raise ValueError('手机号格式不正确')
        
        return phone


class Contact(ContactBase):
    """
    类级注释：联系人响应模式
    """
    id: str = Field(..., description="联系人ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    model_config = {
        "from_attributes": True
    }
