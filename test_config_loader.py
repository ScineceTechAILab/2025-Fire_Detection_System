"""
类级注释：测试配置加载器
验证修改后的 config_hot_loader 是否能从新的 admin-backend 配置中读取数据
"""
import logging
from utils.logging_config import setup_logging

setup_logging(log_dir="log", log_level=logging.INFO)

from core.communication.config_hot_loader import get_config_hot_loader


def main():
    """
    函数级注释：主测试函数
    """
    print("=" * 60)
    print("测试配置加载器")
    print("=" * 60)
    
    config_loader = get_config_hot_loader()
    
    print("\n📋 测试获取配置:")
    print("-" * 60)
    
    # 测试飞书配置
    feishu_app_id = config_loader.get_config("feishu_app_id")
    feishu_app_secret = config_loader.get_config("feishu_app_secret")
    feishu_group_chat_id = config_loader.get_config("feishu_group_chat_id")
    
    print(f"feishu_app_id: {feishu_app_id}")
    print(f"feishu_app_secret: {'*' * 10 if feishu_app_secret else 'None'}")
    print(f"feishu_group_chat_id: {feishu_group_chat_id}")
    
    # 测试阿里云配置
    ali_access_key_id = config_loader.get_config("ali_access_key_id")
    ali_sms_sign_name = config_loader.get_config("ali_sms_sign_name")
    
    print(f"\nali_access_key_id: {ali_access_key_id}")
    print(f"ali_sms_sign_name: {ali_sms_sign_name}")
    
    print("\n👥 测试获取接收人:")
    print("-" * 60)
    
    feishu_recipients = config_loader.get_feishu_recipients()
    sms_recipients = config_loader.get_sms_recipients()
    
    print(f"飞书接收人: {len(feishu_recipients)} 人")
    for r in feishu_recipients:
        print(f"  - {r.get('name')}: {r.get('feishu_open_id')}")
    
    print(f"\n短信接收人: {len(sms_recipients)} 人")
    for r in sms_recipients:
        print(f"  - {r.get('name')}: {r.get('phone')}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
