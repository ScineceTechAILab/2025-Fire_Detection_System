"""
类级注释：.env 到 config_items.json 迁移脚本
将 .env 文件中的配置迁移到后端 JSON 配置存储
"""
import os
import sys
import json
import uuid
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from cryptography.fernet import Fernet


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EnvMigration")


# 从 security.py 复制的加密函数（避免依赖）
def _get_fernet_key() -> bytes:
    """
    获取或生成 Fernet 密钥
    """
    key_file = Path(__file__).parent / "backend" / ".secret_key"
    if key_file.exists():
        with open(key_file, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    key_file.parent.mkdir(exist_ok=True)
    with open(key_file, 'wb') as f:
        f.write(key)
    return key


def encrypt_value(value: str) -> str:
    """
    加密值
    """
    key = _get_fernet_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()


class EnvMigration:
    """
    类级注释：环境变量迁移类
    """
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent
        self.env_path = self.project_root / ".env"
        self.backend_data_dir = self.project_root / "backend" / "data"
        self.config_items_path = self.backend_data_dir / "config_items.json"
        self.config_groups_path = self.backend_data_dir / "config_groups.json"
        
        # 加载配置分组
        self.config_groups = self._load_config_groups()
        
        # 配置项元数据映射
        self.config_metadata = self._get_config_metadata()
        
        # 迁移统计
        self.stats = {
            'total': 0,
            'updated': 0,
            'added': 0,
            'skipped': 0,
            'sensitive': [],
            'value_changed': []
        }
    
    def _load_config_groups(self) -> Dict[str, Dict[str, Any]]:
        """
        函数级注释：加载配置分组
        """
        if not self.config_groups_path.exists():
            logger.error(f"配置分组文件不存在: {self.config_groups_path}")
            return {}
        
        with open(self.config_groups_path, 'r', encoding='utf-8') as f:
            groups = json.load(f)
        
        # 按 code 建立索引
        group_map = {}
        for group in groups:
            group_map[group['code']] = group
        return group_map
    
    def _get_config_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        函数级注释：获取配置项元数据映射
        """
        feishu_group_id = self.config_groups.get('feishu', {}).get('id')
        aliyun_group_id = self.config_groups.get('aliyun', {}).get('id')
        system_group_id = self.config_groups.get('system', {}).get('id')
        
        return {
            # 飞书配置
            'feishu_app_id': {
                'group_id': feishu_group_id,
                'label': '飞书App ID',
                'description': '飞书开放平台应用ID',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': True,
                'sort_order': 1
            },
            'feishu_app_secret': {
                'group_id': feishu_group_id,
                'label': '飞书App Secret',
                'description': '飞书开放平台应用密钥',
                'value_type': 'password',
                'is_encrypted': True,
                'is_required': True,
                'sort_order': 2
            },
            'feishu_group_chat_id': {
                'group_id': feishu_group_id,
                'label': '飞书群聊ID',
                'description': '火灾报警群聊ID',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': True,
                'sort_order': 3
            },
            'feishu_keyword': {
                'group_id': feishu_group_id,
                'label': '消息关键词',
                'description': '群消息关键词前缀',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 4
            },
            'feishuwebhook': {
                'group_id': feishu_group_id,
                'label': '飞书Webhook URL',
                'description': '飞书机器人Webhook地址',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 5
            },
            # 阿里云配置
            'ali_access_key_id': {
                'group_id': aliyun_group_id,
                'label': '阿里云AccessKey ID',
                'description': '阿里云RAM用户AccessKey ID',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': True,
                'sort_order': 1
            },
            'ali_access_key_secret': {
                'group_id': aliyun_group_id,
                'label': '阿里云AccessKey Secret',
                'description': '阿里云RAM用户AccessKey密钥',
                'value_type': 'password',
                'is_encrypted': True,
                'is_required': True,
                'sort_order': 2
            },
            'ali_sms_sign_name': {
                'group_id': aliyun_group_id,
                'label': '短信签名',
                'description': '阿里云短信签名名称',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': True,
                'sort_order': 3
            },
            'ali_sms_template_code': {
                'group_id': aliyun_group_id,
                'label': '短信模板编码',
                'description': '阿里云短信模板CODE',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': True,
                'sort_order': 4
            },
            'endpoint': {
                'group_id': aliyun_group_id,
                'label': 'OSS Endpoint',
                'description': '阿里云OSS服务端点',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 5
            },
            'bucket_name': {
                'group_id': aliyun_group_id,
                'label': 'OSS Bucket名称',
                'description': '阿里云OSS存储桶名称',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 6
            },
            # 系统配置（管理员手机号）
            'admin_phone1': {
                'group_id': system_group_id,
                'label': '管理员手机号1',
                'description': '管理员1的手机号',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 10
            },
            'admin_phone2': {
                'group_id': system_group_id,
                'label': '管理员手机号2',
                'description': '管理员2的手机号',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 11
            },
            'admin_phon2': {
                'group_id': system_group_id,
                'label': '管理员手机号2',
                'description': '管理员2的手机号（拼写错误版本）',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 11
            },
            'sms_phone1': {
                'group_id': system_group_id,
                'label': '短信接收人手机号1',
                'description': '短信接收人1的手机号',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 12
            },
            'sms_phone2': {
                'group_id': system_group_id,
                'label': '短信接收人手机号2',
                'description': '短信接收人2的手机号',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 13
            },
            'sms_phon2': {
                'group_id': system_group_id,
                'label': '短信接收人手机号2',
                'description': '短信接收人2的手机号（拼写错误版本）',
                'value_type': 'string',
                'is_encrypted': False,
                'is_required': False,
                'sort_order': 13
            }
        }
    
    def _parse_env_file(self) -> Dict[str, str]:
        """
        函数级注释：解析 .env 文件
        """
        if not self.env_path.exists():
            logger.error(f".env 文件不存在: {self.env_path}")
            return {}
        
        env_vars = {}
        with open(self.env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    env_vars[key] = value
        
        logger.info(f"从 .env 解析到 {len(env_vars)} 个配置项")
        return env_vars
    
    def _load_config_items(self) -> List[Dict[str, Any]]:
        """
        函数级注释：加载现有配置项
        """
        if not self.config_items_path.exists():
            logger.warning(f"配置项文件不存在: {self.config_items_path}")
            return []
        
        with open(self.config_items_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_config_items(self, config_items: List[Dict[str, Any]]):
        """
        函数级注释：保存配置项
        """
        # 备份原文件
        if self.config_items_path.exists():
            backup_path = self.config_items_path.with_suffix(
                f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            import shutil
            shutil.copy2(self.config_items_path, backup_path)
            logger.info(f"已备份原配置文件到: {backup_path}")
        
        with open(self.config_items_path, 'w', encoding='utf-8') as f:
            json.dump(config_items, f, ensure_ascii=False, indent=2)
        
        logger.info(f"配置项已保存到: {self.config_items_path}")
    
    def _create_config_item(self, key: str, value: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        函数级注释：创建新配置项
        """
        now = datetime.now().isoformat()
        
        # 处理加密
        stored_value = value
        if metadata.get('is_encrypted'):
            stored_value = encrypt_value(value)
        
        return {
            'id': str(uuid.uuid4()),
            'group_id': metadata.get('group_id'),
            'key': key,
            'value': stored_value,
            'value_type': metadata.get('value_type', 'string'),
            'label': metadata.get('label', key),
            'description': metadata.get('description', ''),
            'is_encrypted': metadata.get('is_encrypted', False),
            'is_required': metadata.get('is_required', False),
            'is_active': True,
            'placeholder': None,
            'default_value': None,
            'sort_order': metadata.get('sort_order', 999),
            'validation_rule': None,
            'created_at': now,
            'updated_at': now,
            'created_by': 'env_migration',
            'updated_by': 'env_migration'
        }
    
    def _update_config_item(self, item: Dict[str, Any], value: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        函数级注释：更新现有配置项
        """
        now = datetime.now().isoformat()
        
        # 处理加密
        stored_value = value
        if item.get('is_encrypted') or metadata.get('is_encrypted'):
            stored_value = encrypt_value(value)
        
        # 检查值是否变化
        old_value = item.get('value')
        if old_value != stored_value:
            self.stats['value_changed'].append({
                'key': item.get('key'),
                'old_value': '******' if item.get('is_encrypted') else old_value,
                'new_value': '******' if (item.get('is_encrypted') or metadata.get('is_encrypted')) else value
            })
        
        item.update({
            'value': stored_value,
            'label': metadata.get('label', item.get('label')),
            'description': metadata.get('description', item.get('description')),
            'is_encrypted': metadata.get('is_encrypted', item.get('is_encrypted')),
            'is_required': metadata.get('is_required', item.get('is_required')),
            'sort_order': metadata.get('sort_order', item.get('sort_order')),
            'updated_at': now,
            'updated_by': 'env_migration'
        })
        
        return item
    
    def migrate(self):
        """
        函数级注释：执行迁移
        """
        logger.info("=" * 60)
        logger.info("开始 .env 配置迁移")
        logger.info("=" * 60)
        
        # 1. 解析 .env
        env_vars = self._parse_env_file()
        if not env_vars:
            logger.error("没有找到可迁移的配置项")
            return
        
        # 2. 加载现有配置
        config_items = self._load_config_items()
        
        # 3. 按 key 建立索引
        existing_items = {}
        for item in config_items:
            existing_items[item.get('key')] = item
        
        # 4. 处理每个环境变量
        for key, value in env_vars.items():
            self.stats['total'] += 1
            
            # 标准化 key（转小写，处理大小写不一致）
            normalized_key = key.lower()
            
            # 查找元数据
            metadata = self.config_metadata.get(normalized_key)
            if not metadata:
                logger.warning(f"未知配置项: {key}，跳过")
                self.stats['skipped'] += 1
                continue
            
            # 检查是否是敏感信息
            if metadata.get('is_encrypted'):
                self.stats['sensitive'].append({
                    'key': key,
                    'label': metadata.get('label')
                })
            
            if normalized_key in existing_items:
                # 更新现有配置
                logger.info(f"更新配置项: {key}")
                item = existing_items[normalized_key]
                self._update_config_item(item, value, metadata)
                self.stats['updated'] += 1
            else:
                # 新增配置
                logger.info(f"新增配置项: {key}")
                new_item = self._create_config_item(normalized_key, value, metadata)
                config_items.append(new_item)
                existing_items[normalized_key] = new_item
                self.stats['added'] += 1
        
        # 5. 保存配置
        self._save_config_items(config_items)
        
        # 6. 生成报告
        self._generate_report()
    
    def _generate_report(self):
        """
        函数级注释：生成迁移报告
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("迁移报告")
        logger.info("=" * 60)
        
        logger.info(f"总计处理: {self.stats['total']} 项")
        logger.info(f"  - 更新: {self.stats['updated']} 项")
        logger.info(f"  - 新增: {self.stats['added']} 项")
        logger.info(f"  - 跳过: {self.stats['skipped']} 项")
        
        if self.stats['value_changed']:
            logger.info("")
            logger.info("值发生变化的配置项:")
            for item in self.stats['value_changed']:
                logger.info(f"  - {item['key']}: {item['old_value']} -> {item['new_value']}")
        
        if self.stats['sensitive']:
            logger.info("")
            logger.info("【需要人工复核】敏感信息配置项:")
            for item in self.stats['sensitive']:
                logger.info(f"  - {item['label']} ({item['key']})")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("迁移完成！")
        logger.info("=" * 60)


if __name__ == "__main__":
    migration = EnvMigration()
    migration.migrate()
