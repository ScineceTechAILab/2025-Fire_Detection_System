"""
类级注释：系统参数管理路由
提供系统参数的 CRUD、版本控制、审计日志、导入导出等 API
"""
from fastapi import APIRouter, Query, UploadFile, File, HTTPException, Request, Depends
from typing import Optional, List, Dict, Any

from ..schemas.common import Response
from ..schemas.system import (
    SystemParam, ParamCategory, SystemConfigUpdate,
    SystemConfigResponse, ParamVersion, ParamAuditLog,
    VersionCompareResponse
)
from ..services.system_service import get_system_param_service
from .auth import require_auth, require_csrf

router = APIRouter(prefix="/system", tags=["系统参数管理"], dependencies=[Depends(require_auth), Depends(require_csrf)])
system_service = get_system_param_service()


@router.get("/params", response_model=Response[SystemConfigResponse])
def get_params(
    category: Optional[ParamCategory] = Query(None, description="参数分类")
):
    """
    函数级注释：获取系统参数列表
    """
    params = system_service.get_all_params(category)
    total_count = len(params)
    
    last_updated = None
    if params:
        last_updated = max(p.updated_at for p in params)
    
    return Response.success(
        data=SystemConfigResponse(
            params=params,
            total_count=total_count,
            last_updated=last_updated
        )
    )


@router.get("/params/{key}", response_model=Response[SystemParam])
def get_param(key: str):
    """
    函数级注释：获取单个参数详情
    """
    param = system_service.get_param(key)
    if not param:
        raise HTTPException(status_code=404, detail=f"参数 {key} 不存在")
    return Response.success(data=param)


@router.put("/params", response_model=Response[List[SystemParam]])
async def update_params(
    update: SystemConfigUpdate,
    request: Request
):
    """
    函数级注释：批量更新参数
    """
    client_host = request.client.host if request.client else None
    
    try:
        updated_params = system_service.update_params(update, ip_address=client_host)
        
        # 检查是否有需要重启的参数
        requires_restart = any(p.requires_restart for p in updated_params)
        
        msg = "参数更新成功"
        if requires_restart:
            msg += "（部分参数需要重启才能生效）"
        
        return Response.success(data=updated_params, msg=msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/params/{key}/versions", response_model=Response[List[ParamVersion]])
def get_param_versions(
    key: str,
    limit: int = Query(20, ge=1, le=100, description="返回数量限制")
):
    """
    函数级注释：获取参数的历史版本
    """
    param = system_service.get_param(key)
    if not param:
        raise HTTPException(status_code=404, detail=f"参数 {key} 不存在")
    
    versions = system_service.get_param_versions(key, limit)
    return Response.success(data=versions)


@router.post("/params/{key}/rollback/{version_id}", response_model=Response[SystemParam])
def rollback_param(
    key: str,
    version_id: str,
    request: Request,
    operator: Optional[str] = Query(None, description="操作人")
):
    """
    函数级注释：回滚参数到指定版本
    """
    client_host = request.client.host if request.client else None
    
    param = system_service.rollback_param(key, version_id, operator)
    if not param:
        raise HTTPException(status_code=404, detail="参数或版本不存在")
    
    return Response.success(data=param, msg="参数回滚成功")


@router.get("/audit-logs", response_model=Response[List[ParamAuditLog]])
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500, description="返回数量限制")
):
    """
    函数级注释：获取审计日志
    """
    logs = system_service.get_audit_logs(limit)
    return Response.success(data=logs)


@router.get("/export", response_model=Response[Dict[str, Any]])
def export_config():
    """
    函数级注释：导出配置
    """
    config_data = system_service.export_config()
    return Response.success(data=config_data, msg="配置导出成功")


@router.post("/import", response_model=Response[None])
async def import_config(
    file: UploadFile = File(..., description="配置文件"),
    request: Request = None,
    operator: Optional[str] = Query(None, description="操作人")
):
    """
    函数级注释：导入配置
    """
    try:
        content = await file.read()
        import json
        config_data = json.loads(content)
        
        client_host = request.client.host if request and request.client else None
        system_service.import_config(config_data, operator, client_host)
        
        return Response.success(msg="配置导入成功")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 格式")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.post("/reload", response_model=Response[None])
def reload_config():
    """
    函数级注释：重新加载配置（热加载）
    """
    from ..core.storage import get_storage_manager
    storage = get_storage_manager()
    storage.reload()
    return Response.success(msg="配置重新加载成功")


@router.get("/restart-required", response_model=Response[List[str]])
def get_restart_required_params():
    """
    函数级注释：获取需要重启的参数列表
    """
    params = system_service.get_all_params()
    restart_params = [p.key for p in params if p.requires_restart]
    return Response.success(data=restart_params)
