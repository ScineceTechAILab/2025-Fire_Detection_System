"""
类级注释：飞书管理模块测试
"""
import pytest
import json
import os
import shutil
from pathlib import Path

from app.main import app

TEST_CONFIG_DIR = Path("test_config")


@pytest.fixture(autouse=True)
def setup_test_config():
    """
    函数级注释：测试前后清理配置目录
    """
    if TEST_CONFIG_DIR.exists():
        shutil.rmtree(TEST_CONFIG_DIR)
    TEST_CONFIG_DIR.mkdir(exist_ok=True)
    
    original_env = os.environ.get("CONFIG_DIR")
    os.environ["CONFIG_DIR"] = str(TEST_CONFIG_DIR)
    
    yield
    
    if original_env:
        os.environ["CONFIG_DIR"] = original_env
    else:
        os.environ.pop("CONFIG_DIR", None)
    
    if TEST_CONFIG_DIR.exists():
        shutil.rmtree(TEST_CONFIG_DIR)


def test_get_feishu_config(client, auth_headers):
    """
    函数级注释：测试获取飞书配置
    """
    response = client.get("/api/v1/feishu", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "group_chat_id" in data["data"]
    assert "contacts" in data["data"]


def test_update_group_chat_id(client, write_headers):
    """
    函数级注释：测试更新群聊ID
    """
    test_chat_id = "oc_test_123456"
    response = client.put(
        "/api/v1/feishu/group-chat",
        json={"group_chat_id": test_chat_id}
        ,headers=write_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["group_chat_id"] == test_chat_id


def test_create_contact(client, write_headers):
    """
    函数级注释：测试创建联系人
    """
    contact_data = {
        "name": "张三",
        "identity": "管理员",
        "phone": "18903690733"
    }
    response = client.post(
        "/api/v1/feishu/contacts",
        json=contact_data,
        headers=write_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == "张三"
    assert data["data"]["phone"] == "+8618903690733"


def test_create_contact_invalid_phone(client, write_headers):
    """
    函数级注释：测试创建联系人时手机号格式错误
    """
    contact_data = {
        "name": "李四",
        "identity": "管理员",
        "phone": "12345"
    }
    response = client.post(
        "/api/v1/feishu/contacts",
        json=contact_data,
        headers=write_headers
    )
    assert response.status_code == 422


def test_get_contacts(client, auth_headers, write_headers):
    """
    函数级注释：测试获取联系人列表
    """
    contact_data = {
        "name": "王五",
        "identity": "管理员",
        "phone": "18296984043"
    }
    client.post("/api/v1/feishu/contacts", json=contact_data, headers=write_headers)
    
    response = client.get("/api/v1/feishu/contacts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert len(data["data"]) >= 1


def test_update_contact(client, write_headers):
    """
    函数级注释：测试更新联系人
    """
    create_response = client.post(
        "/api/v1/feishu/contacts",
        json={"name": "赵六", "identity": "管理员", "phone": "18903690733"},
        headers=write_headers
    )
    contact_id = create_response.json()["data"]["id"]
    
    update_response = client.put(
        f"/api/v1/feishu/contacts/{contact_id}",
        json={"name": "赵六（已更新）"},
        headers=write_headers
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == "赵六（已更新）"


def test_delete_contact(client, write_headers):
    """
    函数级注释：测试删除联系人
    """
    create_response = client.post(
        "/api/v1/feishu/contacts",
        json={"name": "钱七", "identity": "管理员", "phone": "18903690733"},
        headers=write_headers
    )
    contact_id = create_response.json()["data"]["id"]
    
    delete_response = client.delete(f"/api/v1/feishu/contacts/{contact_id}", headers=write_headers)
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["code"] == 200


def test_delete_nonexistent_contact(client, write_headers):
    """
    函数级注释：测试删除不存在的联系人
    """
    response = client.delete("/api/v1/feishu/contacts/nonexistent-id", headers=write_headers)
    assert response.status_code == 404
