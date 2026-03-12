"""
类级注释：配置管理
使用 python-dotenv 从 .env 文件读取静态敏感信息
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    类级注释：应用配置
    """
    # 飞书配置（从 .env 读取）
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    
    # 阿里云配置（从 .env 读取）
    ali_access_key_id: str = ""
    ali_access_key_secret: str = ""
    
    # 应用配置
    app_name: str = "Fire Detection Admin System"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # CORS 配置
    backend_cors_origins: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings():
    """
    函数级注释：获取配置单例
    """
    return Settings()
