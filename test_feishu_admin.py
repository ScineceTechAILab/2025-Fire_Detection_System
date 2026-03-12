"""
类级注释：测试飞书管理员加载功能
验证修改后的 get_admin_ids 是否能通过手机号获取 open_id
"""
import logging
from utils.logging_config import setup_logging

setup_logging(log_dir="log", log_level=logging.INFO)

from core.communication.feishu import FeishuNotifier


def main():
    """
    函数级注释：主测试函数
    """
    print("=" * 60)
    print("测试飞书管理员加载功能")
    print("=" * 60)
    
    notifier = FeishuNotifier()
    
    print("\n📋 获取管理员列表:")
    print("-" * 60)
    
    admin_ids = notifier.get_admin_ids(force_refresh=True)
    
    print(f"\n管理员 ID 列表: {admin_ids}")
    print(f"共 {len(admin_ids)} 位管理员")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
