"""
类级注释：获取飞书群聊ID的简化版本
直接从 .env 文件读取配置，不依赖旧系统的配置加载器
"""
import os
import requests
from dotenv import load_dotenv
from pathlib import Path


def get_tenant_access_token(app_id: str, app_secret: str):
    """
    函数级注释：获取飞书租户访问令牌
    """
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": app_id, "app_secret": app_secret}
    
    try:
        resp = requests.post(url, json=data)
        result = resp.json()
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            print(f"❌ 获取 Token 失败: {result}")
            return None
    except Exception as e:
        print(f"❌ 获取 Token 异常: {e}")
        return None


def get_group_list(token: str):
    """
    函数级注释：获取机器人所在的群列表
    """
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        resp = requests.get(url, headers=headers)
        result = resp.json()
        if result.get("code") == 0:
            return result.get("data", {}).get("items", [])
        else:
            print(f"❌ 获取群列表失败: {result}")
            return None
    except Exception as e:
        print(f"❌ 获取群列表异常: {e}")
        return None


def main():
    """
    函数级注释：主函数
    """
    print("=" * 60)
    print("获取飞书群聊 ID")
    print("=" * 60)
    
    # 加载 .env 文件
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"❌ .env 文件不存在: {env_path}")
        return
    
    load_dotenv(dotenv_path=env_path)
    
    app_id = os.getenv("feishu_app_id")
    app_secret = os.getenv("feishu_app_secret")
    
    if not app_id or not app_secret:
        print("❌ 未配置飞书 App ID 或 App Secret")
        print("请检查 .env 文件中的 feishu_app_id 和 feishu_app_secret")
        return
    
    print(f"✅ 读取配置成功")
    print(f"   App ID: {app_id}")
    
    # 获取 Token
    print("\n正在获取租户访问令牌...")
    token = get_tenant_access_token(app_id, app_secret)
    if not token:
        return
    
    print("✅ 获取 Token 成功")
    
    # 获取群列表
    print("\n正在获取群列表...")
    groups = get_group_list(token)
    if groups is None:
        return
    
    if not groups:
        print("⚠️ 未找到任何群聊")
        print("请确保机器人已被邀请到群聊中")
        return
    
    print(f"\n✅ 找到 {len(groups)} 个群聊:")
    print("-" * 60)
    
    for idx, group in enumerate(groups, 1):
        chat_id = group.get("chat_id", "")
        name = group.get("name", "未知群聊")
        print(f"{idx}. 群名称: {name}")
        print(f"   群聊 ID: {chat_id}")
        print("-" * 60)
    
    print("\n💡 提示:")
    print("1. 复制上面的群聊 ID")
    print("2. 打开管理后台 http://localhost:5173")
    print("3. 在「飞书管理」页面粘贴并保存")


if __name__ == "__main__":
    main()
