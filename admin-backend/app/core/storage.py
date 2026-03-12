"""
类级注释：JSON 文件存储管理器
提供 JSON 文件的读写、锁定、备份、热加载功能
"""
import json
import os
import threading
import time
import shutil
from pathlib import Path
from typing import TypeVar, Type, Optional, List, Dict, Any
from datetime import datetime

T = TypeVar('T')


class JSONStorageManager:
    """
    类级注释：JSON 文件存储管理器
    负责 JSON 文件的读写、并发控制和热加载
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        函数级注释：初始化存储管理器
        :param config_dir: 配置存储目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.locks: Dict[str, threading.RLock] = {}
        self.global_lock = threading.RLock()
        
        # 内存缓存
        self._cache: Dict[str, Any] = {}
        self._file_mtimes: Dict[str, float] = {}
        
        self._init_default_files()
    
    def _init_default_files(self):
        """
        函数级注释：初始化默认配置文件
        """
        default_files = {
            "feishu.json": {
                "group_chat_id": "",
                "contacts": []
            },
            "sms.json": {
                "contacts": []
            },
            "admin.json": {
                "user": "admin",
                "password": "$2b$12$WWgUKZsT8Lq8Fb4E2NBAm.nwGZinR21XtGJFwTaQR./GiTNIar5/e"
            },
            "system.json": None,
            "system_versions.json": None,
            "system_audit.json": None
        }
        
        for filename, default_data in default_files.items():
            file_path = self.config_dir / filename
            if not file_path.exists() and default_data is not None:
                self._write_json_safe(file_path, default_data)
                self._cache[filename] = default_data
                self._file_mtimes[filename] = file_path.stat().st_mtime
    
    def _get_lock(self, file_name: str) -> threading.RLock:
        """
        函数级注释：获取文件锁
        """
        with self.global_lock:
            if file_name not in self.locks:
                self.locks[file_name] = threading.RLock()
            return self.locks[file_name]
    
    def _write_json_safe(self, file_path: Path, data: Any):
        """
        函数级注释：安全写入 JSON 文件（原子操作）
        """
        temp_path = file_path.with_suffix('.tmp')
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            if os.name == 'nt':
                if file_path.exists():
                    file_path.unlink()
                temp_path.rename(file_path)
            else:
                temp_path.rename(file_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def read(self, file_name: str, use_cache: bool = True) -> Any:
        """
        函数级注释：读取 JSON 文件
        :param file_name: 文件名
        :param use_cache: 是否使用缓存
        :return: JSON 数据
        """
        file_path = self.config_dir / file_name
        lock = self._get_lock(file_name)
        
        with lock:
            if not file_path.exists():
                return None
            
            if use_cache:
                mtime = file_path.stat().st_mtime
                if file_name in self._cache and self._file_mtimes.get(file_name, 0) >= mtime:
                    return self._cache[file_name]
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._cache[file_name] = data
                self._file_mtimes[file_name] = file_path.stat().st_mtime
                return data
            except (json.JSONDecodeError, IOError):
                return None
    
    def write(self, file_name: str, data: Any):
        """
        函数级注释：写入 JSON 文件
        :param file_name: 文件名
        :param data: 要写入的数据
        """
        file_path = self.config_dir / file_name
        lock = self._get_lock(file_name)
        
        with lock:
            self._write_json_safe(file_path, data)
            self._cache[file_name] = data
            self._file_mtimes[file_name] = file_path.stat().st_mtime
    
    def reload(self, file_name: Optional[str] = None):
        """
        函数级注释：重新加载配置
        :param file_name: 指定文件名，None 则重新加载所有
        """
        if file_name:
            self.read(file_name, use_cache=False)
        else:
            for filename in ["feishu.json", "sms.json"]:
                self.read(filename, use_cache=False)


# 全局存储管理器实例
_storage_manager: Optional[JSONStorageManager] = None


def get_storage_manager() -> JSONStorageManager:
    """
    函数级注释：获取全局存储管理器实例（单例模式）
    """
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = JSONStorageManager()
    return _storage_manager
