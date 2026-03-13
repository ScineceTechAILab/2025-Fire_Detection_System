"""
类级注释：配置管理
从 credentials.json 读取敏感配置，保持与主程序配置源一致
"""
import json
from pathlib import Path
from functools import lru_cache


class Settings:
    """
    类级注释：应用配置
    """
    
    def __init__(self):
        self.app_name: str = "Fire Detection Admin System"
        self.app_version: str = "1.0.0"
        self.debug: bool = True
        self.backend_cors_origins: list = ["*"]
        
        # 从 credentials.json 加载敏感配置
        self.feishu_app_id: str = ""
        self.feishu_app_secret: str = ""
        self.ali_access_key_id: str = ""
        self.ali_access_key_secret: str = ""
        
        self._load_from_credentials()
    
    def _load_from_credentials(self):
        """
        函数级注释：从 credentials.json 加载配置
        """
        config_dir = Path("config")
        credentials_path = config_dir / "credentials.json"
        
        if not credentials_path.exists():
            return
        
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            feishu = data.get("feishu", {})
            self.feishu_app_id = feishu.get("app_id", "")
            self.feishu_app_secret = feishu.get("app_secret", "")
            
            aliyun = data.get("aliyun", {})
            self.ali_access_key_id = aliyun.get("access_key_id", "")
            self.ali_access_key_secret = aliyun.get("access_key_secret", "")
        except Exception:
            pass


@lru_cache()
def get_settings():
    """
    函数级注释：获取配置单例
    """
    return Settings()
