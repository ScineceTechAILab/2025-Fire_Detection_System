"""
类级注释：云短信管理路由
提供短信配置的 REST API 接口
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from ..schemas.common import Response
from ..schemas.sms import SmsConfig
from ..schemas.contact import Contact, ContactCreate, ContactUpdate
from ..services.sms_service import SmsService
from .auth import require_auth, require_csrf

router = APIRouter(prefix="/sms", tags=["云短信管理"], dependencies=[Depends(require_auth), Depends(require_csrf)])
sms_service = SmsService()


@router.get("", response_model=Response[SmsConfig])
def get_sms_config():
    """
    函数级注释：获取短信配置
    """
    config = sms_service.get_config()
    return Response.success(data=config)


@router.get("/contacts", response_model=Response[List[Contact]])
def get_contacts():
    """
    函数级注释：获取紧急联系人列表
    """
    contacts = sms_service.contact_service.get_all()
    return Response.success(data=contacts)


@router.get("/contacts/{contact_id}", response_model=Response[Contact])
def get_contact(contact_id: str):
    """
    函数级注释：获取单个联系人
    """
    contact = sms_service.contact_service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return Response.success(data=contact)


@router.post("/contacts", response_model=Response[Contact], status_code=status.HTTP_201_CREATED)
def create_contact(contact_in: ContactCreate):
    """
    函数级注释：创建联系人
    """
    contact = sms_service.contact_service.create(contact_in.model_dump())
    return Response.success(data=contact, msg="联系人创建成功")


@router.put("/contacts/{contact_id}", response_model=Response[Contact])
def update_contact(contact_id: str, contact_in: ContactUpdate):
    """
    函数级注释：更新联系人
    """
    contact = sms_service.contact_service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    
    updated = sms_service.contact_service.update(contact_id, contact_in.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=500, detail="更新失败")
    
    return Response.success(data=updated, msg="联系人更新成功")


@router.delete("/contacts/{contact_id}", response_model=Response[None])
def delete_contact(contact_id: str):
    """
    函数级注释：删除联系人
    """
    contact = sms_service.contact_service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    
    success = sms_service.contact_service.delete(contact_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return Response.success(msg="联系人删除成功")
