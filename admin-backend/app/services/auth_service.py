"""
类级注释：认证服务
提供从 admin.json 读取账户、密码校验、JWT 签发
"""
import os
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..core.storage import get_storage_manager


class AuthService:
    """
    类级注释：认证服务
    """
    def __init__(self):
        """
        函数级注释：初始化
        """
        self.storage = get_storage_manager()
        # 密钥：优先读取环境变量，否则使用固定值（建议生产通过环境变量注入）
        self.jwt_secret = os.getenv("ADMIN_JWT_SECRET", "change_this_secret")
        self.jwt_alg = "HS256"
        self.jwt_ttl_seconds = int(os.getenv("ADMIN_JWT_TTL", "7200"))
    
    def _load_admin(self) -> Optional[dict]:
        """
        函数级注释：读取 admin.json
        """
        return self.storage.read("admin.json")
    
    def _save_admin(self, data: dict):
        """
        函数级注释：保存 admin.json
        """
        self.storage.write("admin.json", data)
    
    def verify_password(self, plain: str, hashed: str) -> bool:
        """
        函数级注释：校验明文密码与 bcrypt 哈希
        """
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    
    def issue_token(self, user: str) -> Tuple[str, int]:
        """
        函数级注释：签发 JWT 令牌
        :return: (token, expires_in)
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self.jwt_ttl_seconds)
        payload = {
            "sub": user,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp())
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_alg)
        return token, self.jwt_ttl_seconds
    
    def decode_token(self, token: str) -> Optional[dict]:
        """
        函数级注释：解析 JWT，失败返回 None
        """
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_alg])
        except Exception:
            return None
    
    def login(self, user: str, password: str) -> Tuple[bool, str, Optional[Tuple[str, int]]]:
        """
        函数级注释：登录逻辑
        :return: (成功与否, 错误信息或用户名, (token, expires_in))
        """
        admin = self._load_admin()
        if not admin:
            return False, "管理员配置不存在", None

        if user != str(admin.get("user")):
            return False, "用户名或密码错误", None
        
        hashed = str(admin.get("password") or "")
        if not self.verify_password(password, hashed):
            return False, "用户名或密码错误", None

        token, ttl = self.issue_token(user)
        return True, user, (token, ttl)
    
    def generate_csrf(self) -> str:
        """
        函数级注释：生成 CSRF Token (Signed JWT)
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self.jwt_ttl_seconds)
        payload = {
            "type": "csrf",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp())
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_alg)

    def verify_csrf(self, token: str) -> bool:
        """
        函数级注释：校验 CSRF Token
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_alg])
            return payload.get("type") == "csrf"
        except Exception:
            return False


_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """
    函数级注释：获取认证服务单例
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
