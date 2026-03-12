"""
类级注释：飞书管理路由
提供飞书配置的 REST API 接口
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List

from ..schemas.common import Response
from ..schemas.feishu import FeishuConfig, FeishuGroupChatUpdate, FeishuChatItem
from ..schemas.contact import Contact, ContactCreate, ContactUpdate
from ..services.feishu_service import FeishuService
from .auth import require_auth, require_csrf

router = APIRouter(prefix="/feishu", tags=["飞书管理"], dependencies=[Depends(require_auth), Depends(require_csrf)])
feishu_service = FeishuService()


@router.get("", response_model=Response[FeishuConfig])
def get_feishu_config():
    """
    函数级注释：获取飞书配置
    """
    config = feishu_service.get_config()
    return Response.success(data=config)


@router.put("/group-chat", response_model=Response[FeishuConfig])
def update_group_chat_id(update: FeishuGroupChatUpdate):
    """
    函数级注释：更新群聊ID
    """
    config = feishu_service.update_group_chat_id(update.group_chat_id)
    return Response.success(data=config, msg="群聊ID更新成功")


@router.get("/contacts", response_model=Response[List[Contact]])
def get_contacts():
    """
    函数级注释：获取紧急联系人列表
    """
    contacts = feishu_service.contact_service.get_all()
    return Response.success(data=contacts)


@router.get("/contacts/{contact_id}", response_model=Response[Contact])
def get_contact(contact_id: str):
    """
    函数级注释：获取单个联系人
    """
    contact = feishu_service.contact_service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return Response.success(data=contact)


@router.post("/contacts", response_model=Response[Contact], status_code=status.HTTP_201_CREATED)
def create_contact(contact_in: ContactCreate):
    """
    函数级注释：创建联系人
    """
    contact = feishu_service.contact_service.create(contact_in.model_dump())
    return Response.success(data=contact, msg="联系人创建成功")


@router.put("/contacts/{contact_id}", response_model=Response[Contact])
def update_contact(contact_id: str, contact_in: ContactUpdate):
    """
    函数级注释：更新联系人
    """
    contact = feishu_service.contact_service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    
    updated = feishu_service.contact_service.update(contact_id, contact_in.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=500, detail="更新失败")
    
    return Response.success(data=updated, msg="联系人更新成功")


@router.delete("/contacts/{contact_id}", response_model=Response[None])
def delete_contact(contact_id: str):
    """
    函数级注释：删除联系人
    """
    contact = feishu_service.contact_service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    
    success = feishu_service.contact_service.delete(contact_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return Response.success(msg="联系人删除成功")


@router.get("/chats", response_model=Response[List[FeishuChatItem]])
def list_bot_chats(
    page_size: int = Query(50, ge=1, le=100),
    max_pages: int = Query(10, ge=1, le=20),
):
    try:
        items = feishu_service.list_bot_chats(page_size=page_size, max_pages=max_pages)
        return Response.success(data=items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取群聊列表失败: {e}")
