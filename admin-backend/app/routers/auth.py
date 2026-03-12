"""
类级注释：认证路由
提供登录、退出、用户信息接口与 CSRF 策略
"""
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from fastapi import Header, Cookie
from typing import Optional
import os

from ..schemas.common import Response as R
from ..schemas.auth import LoginRequest, LoginResponse, WhoAmI
from ..services.auth_service import get_auth_service

router = APIRouter(prefix="/auth", tags=["认证"])
auth = get_auth_service()


@router.post("/login", response_model=R[LoginResponse])
def login(payload: LoginRequest, response: Response, request: Request):
    """
    函数级注释：登录接口
    """
    ok, user_or_msg, tk = auth.login(payload.user, payload.password)
    if not ok or tk is None:
        raise HTTPException(status_code=401, detail=user_or_msg)
    token, expires_in = tk
    csrf_token = auth.generate_csrf()
    # 写入 CSRF Cookie（SameSite=Lax，非 HttpOnly，前端可读，与 Header 双提交校验）
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        samesite="lax",
        secure=False,
        httponly=False,
        path="/"
    )
    return R.success(data=LoginResponse(token=token, csrf_token=csrf_token, expires_in=expires_in, user=user_or_msg))


def require_auth(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    函数级注释：认证依赖（解析并校验 JWT）
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = auth.decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="令牌无效或已过期")
        return str(payload.get("sub", ""))
    if os.getenv("ADMIN_DISABLE_AUTH") == "1":
        return "test"
    else:
        raise HTTPException(status_code=401, detail="未授权")


def require_csrf(request: Request, x_csrf_token: Optional[str] = Header(default=None)):
    """
    函数级注释：CSRF 校验（验证 Header 中的 Signed Token）
    """
    if os.getenv("ADMIN_DISABLE_AUTH") == "1":
        return
    if request.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        if not x_csrf_token:
            raise HTTPException(status_code=403, detail="CSRF Token 缺失")
        if not auth.verify_csrf(x_csrf_token):
            raise HTTPException(status_code=403, detail="CSRF Token 无效或过期")


@router.get("/me", response_model=R[WhoAmI])
def whoami(user: str = Depends(require_auth)):
    """
    函数级注释：获取当前用户信息
    """
    return R.success(data=WhoAmI(user=user))


@router.post("/logout", response_model=R[None])
def logout(response: Response):
    """
    函数级注释：登出接口（清除 CSRF Cookie）
    """
    response.delete_cookie("csrf_token", path="/")
    return R.success()
