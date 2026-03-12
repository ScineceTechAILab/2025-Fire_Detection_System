"""
类级注释：认证与授权数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """
    类级注释：登录请求体
    """
    user: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """
    类级注释：登录响应体
    """
    token: str = Field(..., description="JWT 令牌")
    csrf_token: str = Field(..., description="CSRF 令牌")
    token_type: str = Field("Bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期秒数")
    user: str = Field(..., description="用户名")


class WhoAmI(BaseModel):
    """
    类级注释：用户信息
    """
    user: str = Field(...)
