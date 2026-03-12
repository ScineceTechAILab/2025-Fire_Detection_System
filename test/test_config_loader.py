"""
类级注释：配置加载器单元测试
测试飞书和短信配置独立加载的各种场景
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest import TestCase

from core.communication.config_hot_loader import ConfigHotLoader


class TestConfigHotLoaderRecipients(TestCase):
    """
    类级注释：测试配置加载器的接收人功能
    """
    
    def setUp(self):
        """
        函数级注释：测试前准备
        """
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        
        # 创建项目根目录结构
        self.project_root = Path(self.temp_dir)
        self.admin_config_dir = self.project_root / "admin-backend" / "config"
        self.admin_config_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_feishu_config(self, contacts):
        """
        函数级注释：创建飞书配置文件
        """
        config = {
            "group_chat_id": "oc_test_chat_id",
            "contacts": contacts
        }
        with open(self.admin_config_dir / "feishu.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def _create_sms_config(self, contacts):
        """
        函数级注释：创建短信配置文件
        """
        config = {
            "contacts": contacts
        }
        with open(self.admin_config_dir / "sms.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def test_both_configs_exist_different_names(self):
        """
        函数级注释：测试飞书与云短信配置同时存在且姓名不同
        """
        self._create_feishu_config([
            {"id": "1", "name": "谢承旭", "phone": "+8613800138001"}
        ])
        self._create_sms_config([
            {"id": "2", "name": "于汶泽", "phone": "+8618903690733"}
        ])
        
        loader = ConfigHotLoader()
        loader.new_config_dir = self.admin_config_dir
        loader.new_feishu_path = self.admin_config_dir / "feishu.json"
        loader.new_sms_path = self.admin_config_dir / "sms.json"
        
        recipients = loader._load_recipients_from_new_admin()
        
        feishu_recipients = [r for r in recipients if r.get('source') == 'feishu']
        sms_recipients = [r for r in recipients if r.get('source') == 'sms']
        
        self.assertEqual(len(feishu_recipients), 1)
        self.assertEqual(len(sms_recipients), 1)
        self.assertEqual(feishu_recipients[0]['name'], '谢承旭')
        self.assertEqual(sms_recipients[0]['name'], '于汶泽')
    
    def test_only_feishu_config_exists(self):
        """
        函数级注释：测试仅存在飞书配置
        """
        self._create_feishu_config([
            {"id": "1", "name": "谢承旭", "phone": "+8613800138001"}
        ])
        
        loader = ConfigHotLoader()
        loader.new_config_dir = self.admin_config_dir
        loader.new_feishu_path = self.admin_config_dir / "feishu.json"
        loader.new_sms_path = self.admin_config_dir / "sms.json"
        
        recipients = loader._load_recipients_from_new_admin()
        
        feishu_recipients = [r for r in recipients if r.get('source') == 'feishu']
        sms_recipients = [r for r in recipients if r.get('source') == 'sms']
        
        self.assertEqual(len(feishu_recipients), 1)
        self.assertEqual(len(sms_recipients), 0)
        self.assertEqual(feishu_recipients[0]['name'], '谢承旭')
    
    def test_only_sms_config_exists(self):
        """
        函数级注释：测试仅存在云短信配置
        """
        self._create_sms_config([
            {"id": "1", "name": "于汶泽", "phone": "+8618903690733"}
        ])
        
        loader = ConfigHotLoader()
        loader.new_config_dir = self.admin_config_dir
        loader.new_feishu_path = self.admin_config_dir / "feishu.json"
        loader.new_sms_path = self.admin_config_dir / "sms.json"
        
        recipients = loader._load_recipients_from_new_admin()
        
        feishu_recipients = [r for r in recipients if r.get('source') == 'feishu']
        sms_recipients = [r for r in recipients if r.get('source') == 'sms']
        
        self.assertEqual(len(feishu_recipients), 0)
        self.assertEqual(len(sms_recipients), 1)
        self.assertEqual(sms_recipients[0]['name'], '于汶泽')
    
    def test_both_configs_same_phone_different_names(self):
        """
        函数级注释：测试飞书与云短信配置同时存在，手机号相同但姓名不同
        """
        self._create_feishu_config([
            {"id": "1", "name": "谢承旭", "phone": "+8618903690733"}
        ])
        self._create_sms_config([
            {"id": "2", "name": "于汶泽", "phone": "+8618903690733"}
        ])
        
        loader = ConfigHotLoader()
        loader.new_config_dir = self.admin_config_dir
        loader.new_feishu_path = self.admin_config_dir / "feishu.json"
        loader.new_sms_path = self.admin_config_dir / "sms.json"
        
        recipients = loader._load_recipients_from_new_admin()
        
        feishu_recipients = [r for r in recipients if r.get('source') == 'feishu']
        sms_recipients = [r for r in recipients if r.get('source') == 'sms']
        
        self.assertEqual(len(feishu_recipients), 1)
        self.assertEqual(len(sms_recipients), 1)
        self.assertEqual(feishu_recipients[0]['name'], '谢承旭')
        self.assertEqual(sms_recipients[0]['name'], '于汶泽')
    
    def test_get_feishu_recipients_only_returns_feishu(self):
        """
        函数级注释：测试 get_feishu_recipients 只返回飞书配置中的联系人
        """
        self._create_feishu_config([
            {"id": "1", "name": "谢承旭", "phone": "+8613800138001"}
        ])
        self._create_sms_config([
            {"id": "2", "name": "于汶泽", "phone": "+8618903690733"}
        ])
        
        loader = ConfigHotLoader()
        loader.new_config_dir = self.admin_config_dir
        loader.new_feishu_path = self.admin_config_dir / "feishu.json"
        loader.new_sms_path = self.admin_config_dir / "sms.json"
        
        recipients = loader._load_recipients_from_new_admin()
        loader._recipients_cache = recipients
        
        feishu_recipients = loader.get_feishu_recipients()
        
        self.assertEqual(len(feishu_recipients), 1)
        self.assertEqual(feishu_recipients[0]['name'], '谢承旭')
    
    def test_get_sms_recipients_only_returns_sms(self):
        """
        函数级注释：测试 get_sms_recipients 只返回短信配置中的联系人
        """
        self._create_feishu_config([
            {"id": "1", "name": "谢承旭", "phone": "+8613800138001"}
        ])
        self._create_sms_config([
            {"id": "2", "name": "于汶泽", "phone": "+8618903690733"}
        ])
        
        loader = ConfigHotLoader()
        loader.new_config_dir = self.admin_config_dir
        loader.new_feishu_path = self.admin_config_dir / "feishu.json"
        loader.new_sms_path = self.admin_config_dir / "sms.json"
        
        recipients = loader._load_recipients_from_new_admin()
        loader._recipients_cache = recipients
        
        sms_recipients = loader.get_sms_recipients()
        
        self.assertEqual(len(sms_recipients), 1)
        self.assertEqual(sms_recipients[0]['name'], '于汶泽')
        self.assertEqual(sms_recipients[0]['phone'], '+8618903690733')


if __name__ == '__main__':
    import unittest
    unittest.main()
