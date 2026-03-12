"""
类级注释：通用数据验证模式
定义统一的响应包装格式
"""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    """
    类级注释：统一响应格式
    """
    code: int = Field(200, description="状态码")
    msg: str = Field("success", description="消息")
    data: Optional[T] = Field(None, description="数据")
    
    @classmethod
    def success(cls, data: Optional[T] = None, msg: str = "success"):
        """
        函数级注释：成功响应
        """
        return cls(code=200, msg=msg, data=data)
    
    @classmethod
    def error(cls, msg: str = "error", code: int = 400):
        """
        函数级注释：错误响应
        """
        return cls(code=code, msg=msg, data=None)
