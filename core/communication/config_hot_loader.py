"""
类级注释：配置热加载服务
提供从后端配置管理系统动态加载配置的功能，支持配置变更的实时感知
兼容旧的 backend/data/ 目录和新的 admin-backend/config/ 目录
"""
import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dotenv import load_dotenv


class ConfigHotLoader:
    """
    类级注释：配置热加载器
    从后端 JSON 存储动态加载配置，支持监听配置变更
    兼容旧的 backend/data/ 目录和新的 admin-backend/config/ 目录
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        函数级注释：初始化配置热加载器
        :param data_dir: 后端数据存储目录路径
        """
        self.logger = logging.getLogger("ConfigHotLoader")
        
        # 确定项目根目录
        current_dir = Path(__file__).resolve().parent
        self.project_root = current_dir.parent.parent if current_dir.name == "communication" else current_dir.parent
        
        # 加载 .env 文件中的静态配置
        self._load_env_config()
        
        # 旧系统配置路径
        self.old_data_dir = self.project_root / "backend" / "data"
        self.old_config_items_path = self.old_data_dir / "config_items.json"
        self.old_recipients_path = self.old_data_dir / "recipients.json"
        
        # 新系统配置路径（admin-backend）
        self.new_config_dir = self.project_root / "admin-backend" / "config"
        self.new_feishu_path = self.new_config_dir / "feishu.json"
        self.new_sms_path = self.new_config_dir / "sms.json"
        self.new_system_path = self.new_config_dir / "system.json"
        
        # 配置缓存
        self._config_cache: Dict[str, Any] = {}
        self._recipients_cache: list = []
        self._config_mtime: dict = {}
        self._recipients_mtime: float = 0
        
        # 监听相关
        self._watch_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._change_callbacks: list = []
        
        # 初始化加载
        self._load_config()
        self._load_recipients()
        
        self.logger.info(f"配置热加载器初始化完成")
        if self.new_config_dir.exists():
            self.logger.info(f"  使用新配置目录: {self.new_config_dir}")
        if self.old_data_dir.exists():
            self.logger.info(f"  使用旧配置目录: {self.old_data_dir}")
    
    def _load_env_config(self):
        """
        函数级注释：从 .env 文件加载静态配置
        """
        env_path = self.project_root / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            self.logger.info(f"加载 .env 配置成功: {env_path}")
    
    def _load_config(self):
        """
        函数级注释：从 JSON 文件加载配置（支持新旧系统）
        """
        configs = {}
        changed = False
        
        # 1. 从 .env 读取静态配置
        env_configs = self._load_from_env()
        if env_configs:
            configs.update(env_configs)
        
        # 2. 从新的 admin-backend/config/ 读取配置
        new_configs = self._load_from_new_admin()
        if new_configs:
            configs.update(new_configs)
        
        # 3. 从旧的 backend/data/ 读取配置（向后兼容）
        old_configs = self._load_from_old_backend()
        if old_configs:
            configs.update(old_configs)
        
        self._config_cache = configs
        self.logger.info(f"配置加载成功，共 {len(configs)} 项配置")
        return True
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        函数级注释：从 .env 文件读取静态配置
        """
        configs = {}
        
        # 飞书配置
        if os.getenv("feishu_app_id"):
            configs["feishu_app_id"] = os.getenv("feishu_app_id")
        if os.getenv("feishu_app_secret"):
            configs["feishu_app_secret"] = os.getenv("feishu_app_secret")
        if os.getenv("feishu_group_chat_id"):
            configs["feishu_group_chat_id"] = os.getenv("feishu_group_chat_id")
        
        # 阿里云配置
        if os.getenv("ALI_ACCESS_KEY_ID"):
            configs["ali_access_key_id"] = os.getenv("ALI_ACCESS_KEY_ID")
        if os.getenv("ALI_ACCESS_KEY_SECRET"):
            configs["ali_access_key_secret"] = os.getenv("ALI_ACCESS_KEY_SECRET")
        if os.getenv("ENDPOINT"):
            configs["oss_endpoint"] = os.getenv("ENDPOINT")
        if os.getenv("BUCKET_NAME"):
            configs["oss_bucket_name"] = os.getenv("BUCKET_NAME")
        if os.getenv("ALI_SMS_SIGN_NAME"):
            configs["ali_sms_sign_name"] = os.getenv("ALI_SMS_SIGN_NAME")
        if os.getenv("ALI_SMS_TEMPLATE_CODE"):
            configs["ali_sms_template_code"] = os.getenv("ALI_SMS_TEMPLATE_CODE")
        
        return configs
    
    def _load_from_new_admin(self) -> Dict[str, Any]:
        """
        函数级注释：从新的 admin-backend/config/ 读取配置
        """
        configs = {}
        
        # 读取飞书配置
        if self.new_feishu_path.exists():
            try:
                with open(self.new_feishu_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 群聊 ID
                if data.get("group_chat_id"):
                    configs["feishu_group_chat_id"] = data["group_chat_id"]
                
                # 记录 mtime
                self._config_mtime["feishu"] = self.new_feishu_path.stat().st_mtime
            except Exception as e:
                self.logger.error(f"加载 feishu.json 失败: {e}")
        
        # 读取系统参数配置
        if self.new_system_path.exists():
            try:
                with open(self.new_system_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取系统参数
                params = data.get("params", {})
                for key, param_data in params.items():
                    if param_data.get("value") is not None:
                        configs[key] = param_data["value"]
                
                # 记录 mtime
                self._config_mtime["system"] = self.new_system_path.stat().st_mtime
            except Exception as e:
                self.logger.error(f"加载 system.json 失败: {e}")
        
        return configs
    
    def _load_from_old_backend(self) -> Dict[str, Any]:
        """
        函数级注释：从旧的 backend/data/ 读取配置（向后兼容）
        """
        configs = {}
        
        if not self.old_config_items_path.exists():
            return configs
        
        try:
            with open(self.old_config_items_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析配置项，构建 key -> value 映射
            for item in data:
                if item.get('is_active', True):
                    key = item.get('key')
                    value = item.get('value')
                    value_type = item.get('value_type', 'string')
                    if key and value is not None:
                        configs[key] = self._convert_value(value, value_type)
            
            # 记录 mtime
            self._config_mtime["old_config"] = self.old_config_items_path.stat().st_mtime
        except Exception as e:
            self.logger.error(f"加载旧配置失败: {e}")
        
        return configs
    
    def _load_recipients(self):
        """
        函数级注释：从 JSON 文件加载接收人（支持新旧系统）
        """
        recipients = []
        
        # 1. 从新的 admin-backend/config/ 读取接收人
        new_recipients = self._load_recipients_from_new_admin()
        recipients.extend(new_recipients)
        
        # 2. 从旧的 backend/data/ 读取接收人（向后兼容）
        old_recipients = self._load_recipients_from_old_backend()
        recipients.extend(old_recipients)
        
        self._recipients_cache = recipients
        
        if recipients:
            self.logger.info(f"接收人加载成功，共 {len(recipients)} 人")
        else:
            self.logger.warning("未找到任何接收人")
        
        return True
    
    def _load_recipients_from_new_admin(self) -> list:
        """
        函数级注释：从新的 admin-backend/config/ 读取接收人
        飞书和短信联系人完全独立，不进行去重
        """
        recipients = []
        
        # 读取飞书联系人 - 仅作为飞书接收人
        if self.new_feishu_path.exists():
            try:
                with open(self.new_feishu_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                contacts = data.get("contacts", [])
                for contact in contacts:
                    recipient = {
                        "name": contact.get("name", ""),
                        "phone": contact.get("phone", ""),
                        "feishu_open_id": "",  # 新系统暂不存储 open_id
                        "is_active": True,
                        "is_feishu_recipient": True,
                        "is_sms_recipient": False,  # 飞书联系人不作为短信接收人
                        "is_phone_recipient": False,
                        "source": "feishu"  # 标记来源
                    }
                    recipients.append(recipient)
                
                # 记录 mtime
                self._config_mtime["feishu_contacts"] = self.new_feishu_path.stat().st_mtime
            except Exception as e:
                self.logger.error(f"加载 feishu.json 联系人失败: {e}")
        
        # 读取短信联系人 - 仅作为短信接收人（不与飞书去重）
        if self.new_sms_path.exists():
            try:
                with open(self.new_sms_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                contacts = data.get("contacts", [])
                
                for contact in contacts:
                    recipient = {
                        "name": contact.get("name", ""),
                        "phone": contact.get("phone", ""),
                        "feishu_open_id": "",
                        "is_active": True,
                        "is_feishu_recipient": False,  # 短信联系人不作为飞书接收人
                        "is_sms_recipient": True,
                        "is_phone_recipient": False,
                        "source": "sms"  # 标记来源
                    }
                    recipients.append(recipient)
                
                # 记录 mtime
                self._config_mtime["sms_contacts"] = self.new_sms_path.stat().st_mtime
            except Exception as e:
                self.logger.error(f"加载 sms.json 联系人失败: {e}")
        
        return recipients
    
    def _load_recipients_from_old_backend(self) -> list:
        """
        函数级注释：从旧的 backend/data/ 读取接收人（向后兼容）
        """
        recipients = []
        
        if not self.old_recipients_path.exists():
            return recipients
        
        try:
            with open(self.old_recipients_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 过滤启用的接收人
            recipients = [r for r in data if r.get('is_active', True)]
            self._recipients_mtime = self.old_recipients_path.stat().st_mtime
        except Exception as e:
            self.logger.error(f"加载旧接收人失败: {e}")
        
        return recipients
    
    def _convert_value(self, value: str, value_type: str) -> Any:
        """
        函数级注释：转换值类型
        """
        if value_type == 'number':
            try:
                return int(value) if '.' not in value else float(value)
            except (ValueError, TypeError):
                return value
        elif value_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == 'json':
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value
    
    def _check_changes(self):
        """
        函数级注释：检查配置文件是否有变更（支持新旧系统）
        """
        changed = False
        
        # 1. 检查新的 admin-backend 配置文件
        if self.new_feishu_path.exists():
            mtime = self.new_feishu_path.stat().st_mtime
            if mtime > self._config_mtime.get("feishu", 0):
                self.logger.info("检测到 feishu.json 变更，重新加载...")
                if self._load_config() and self._load_recipients():
                    changed = True
        
        if self.new_system_path.exists():
            mtime = self.new_system_path.stat().st_mtime
            if mtime > self._config_mtime.get("system", 0):
                self.logger.info("检测到 system.json 变更，重新加载...")
                if self._load_config():
                    changed = True
        
        if self.new_sms_path.exists():
            mtime = self.new_sms_path.stat().st_mtime
            if mtime > self._config_mtime.get("sms_contacts", 0):
                self.logger.info("检测到 sms.json 变更，重新加载...")
                if self._load_recipients():
                    changed = True
        
        # 2. 检查旧的 backend/data/ 配置文件（向后兼容）
        if self.old_config_items_path.exists():
            mtime = self.old_config_items_path.stat().st_mtime
            if mtime > self._config_mtime.get("old_config", 0):
                self.logger.info("检测到旧配置文件变更，重新加载...")
                if self._load_config():
                    changed = True
        
        if self.old_recipients_path.exists():
            mtime = self.old_recipients_path.stat().st_mtime
            if mtime > self._recipients_mtime:
                self.logger.info("检测到旧接收人文件变更，重新加载...")
                if self._load_recipients():
                    changed = True
        
        if changed:
            self._notify_callbacks()
    
    def _notify_callbacks(self):
        """
        函数级注释：通知所有变更回调
        """
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"执行回调失败: {e}")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        函数级注释：获取配置值
        :param key: 配置键
        :param default: 默认值
        :return: 配置值
        """
        # 每次获取前检查是否有变更
        self._check_changes()
        return self._config_cache.get(key, default)
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        函数级注释：获取所有配置
        :return: 配置字典
        """
        self._check_changes()
        return self._config_cache.copy()
    
    def get_sms_recipients(self) -> list:
        """
        函数级注释：获取短信接收人列表
        :return: 短信接收人列表 [{'name': 'xxx', 'phone': 'xxx'}, ...]
        """
        self._check_changes()
        return [
            {'name': r.get('name'), 'phone': r.get('phone')}
            for r in self._recipients_cache
            if r.get('is_sms_recipient', True) and r.get('phone')
        ]
    
    def get_feishu_recipients(self) -> list:
        """
        函数级注释：获取飞书接收人列表
        :return: 飞书接收人列表 [{'name': 'xxx', 'feishu_open_id': 'xxx', 'phone': 'xxx'}, ...]
        """
        self._check_changes()
        return [
            {
                'name': r.get('name'),
                'feishu_open_id': r.get('feishu_open_id', ''),
                'phone': r.get('phone', '')
            }
            for r in self._recipients_cache
            if r.get('is_feishu_recipient', True)
        ]
    
    def get_phone_recipients(self) -> list:
        """
        函数级注释：获取电话接收人列表
        :return: 电话接收人列表 [{'name': 'xxx', 'phone': 'xxx'}, ...]
        """
        self._check_changes()
        return [
            {'name': r.get('name'), 'phone': r.get('phone')}
            for r in self._recipients_cache
            if r.get('is_phone_recipient', False) and r.get('phone')
        ]
    
    def get_all_recipients(self) -> list:
        """
        函数级注释：获取所有接收人
        :return: 接收人列表
        """
        self._check_changes()
        return self._recipients_cache.copy()
    
    def add_change_callback(self, callback: Callable[[], None]):
        """
        函数级注释：添加配置变更回调
        :param callback: 回调函数，配置变更时调用
        """
        self._change_callbacks.append(callback)
        self.logger.info(f"添加配置变更回调，当前回调数: {len(self._change_callbacks)}")
    
    def remove_change_callback(self, callback: Callable[[], None]):
        """
        函数级注释：移除配置变更回调
        :param callback: 要移除的回调函数
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            self.logger.info(f"移除配置变更回调，当前回调数: {len(self._change_callbacks)}")
    
    def start_watch(self, interval: float = 5.0):
        """
        函数级注释：启动后台线程监听配置变更
        :param interval: 检查间隔（秒）
        """
        if self._running:
            self.logger.warning("监听线程已在运行")
            return
        
        self._running = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            daemon=True
        )
        self._watch_thread.start()
        self.logger.info(f"配置监听线程已启动，检查间隔: {interval}秒")
    
    def stop_watch(self):
        """
        函数级注释：停止监听线程
        """
        self._running = False
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=2.0)
        self.logger.info("配置监听线程已停止")
    
    def _watch_loop(self, interval: float):
        """
        函数级注释：监听循环
        """
        while self._running:
            try:
                self._check_changes()
            except Exception as e:
                self.logger.error(f"监听循环异常: {e}")
            time.sleep(interval)
    
    def reload(self):
        """
        函数级注释：强制重新加载配置
        """
        self.logger.info("强制重新加载配置...")
        self._load_config()
        self._load_recipients()
        self._notify_callbacks()


# 全局配置热加载器实例
_config_hot_loader: Optional[ConfigHotLoader] = None


def get_config_hot_loader() -> ConfigHotLoader:
    """
    函数级注释：获取全局配置热加载器实例（单例模式）
    :return: ConfigHotLoader 实例
    """
    global _config_hot_loader
    if _config_hot_loader is None:
        _config_hot_loader = ConfigHotLoader()
    return _config_hot_loader
