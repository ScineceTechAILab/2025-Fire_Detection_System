"""
类级注释：凭证管理路由
提供飞书、阿里云等第三方服务凭证的 CRUD API
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from ..schemas.common import Response
from ..services.credentials_service import get_credentials_service
from .auth import require_auth, require_csrf


class FeishuCredentialsUpdate(BaseModel):
    """
    类级注释：飞书凭证更新请求
    """
    app_id: str
    app_secret: str


class AliyunCredentialsUpdate(BaseModel):
    """
    类级注释：阿里云凭证更新请求
    """
    access_key_id: str
    access_key_secret: str
    sms_sign_name: str
    sms_template_code: str


class SmsProviderUpdate(BaseModel):
    """
    类级注释：短信服务商更新请求
    """
    provider: str


router = APIRouter(prefix="/credentials", tags=["凭证管理"], dependencies=[Depends(require_auth), Depends(require_csrf)])
credentials_service = get_credentials_service()


@router.get("", response_model=Response[Dict[str, Any]])
def get_credentials():
    """
    函数级注释：获取所有凭证配置
    """
    credentials = credentials_service.get_credentials()
    return Response.success(data=credentials)


@router.get("/feishu", response_model=Response[Dict[str, str]])
def get_feishu_credentials():
    """
    函数级注释：获取飞书凭证
    """
    credentials = credentials_service.get_feishu_credentials()
    return Response.success(data=credentials)


@router.put("/feishu", response_model=Response[Dict[str, Any]])
def update_feishu_credentials(update: FeishuCredentialsUpdate):
    """
    函数级注释：更新飞书凭证
    """
    try:
        credentials = credentials_service.update_feishu_credentials(
            app_id=update.app_id,
            app_secret=update.app_secret
        )
        return Response.success(data=credentials, msg="飞书凭证更新成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/aliyun", response_model=Response[Dict[str, str]])
def get_aliyun_credentials():
    """
    函数级注释：获取阿里云凭证
    """
    credentials = credentials_service.get_aliyun_credentials()
    return Response.success(data=credentials)


@router.put("/aliyun", response_model=Response[Dict[str, Any]])
def update_aliyun_credentials(update: AliyunCredentialsUpdate):
    """
    函数级注释：更新阿里云凭证
    """
    try:
        credentials = credentials_service.update_aliyun_credentials(
            access_key_id=update.access_key_id,
            access_key_secret=update.access_key_secret,
            sms_sign_name=update.sms_sign_name,
            sms_template_code=update.sms_template_code
        )
        return Response.success(data=credentials, msg="阿里云凭证更新成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sms-provider", response_model=Response[str])
def get_sms_provider():
    """
    函数级注释：获取当前短信服务商
    """
    provider = credentials_service.get_sms_provider()
    return Response.success(data=provider)


@router.put("/sms-provider", response_model=Response[Dict[str, Any]])
def update_sms_provider(update: SmsProviderUpdate):
    """
    函数级注释：更新短信服务商
    """
    try:
        credentials = credentials_service.update_sms_provider(update.provider)
        return Response.success(data=credentials, msg="短信服务商更新成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
