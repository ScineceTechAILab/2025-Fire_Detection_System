"""
类级注释：云短信管理模块测试
"""
import pytest
import os
import shutil
from pathlib import Path

from app.main import app

TEST_CONFIG_DIR = Path("test_config_sms")


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


def test_get_sms_config(client, auth_headers):
    """
    函数级注释：测试获取短信配置
    """
    response = client.get("/api/v1/sms", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "contacts" in data["data"]


def test_sms_contact_crud(client, auth_headers, write_headers):
    """
    函数级注释：测试短信联系人CRUD操作
    """
    contact_data = {
        "name": "短信接收人",
        "identity": "接收人",
        "phone": "18903690733"
    }
    
    create_response = client.post("/api/v1/sms/contacts", json=contact_data, headers=write_headers)
    assert create_response.status_code == 201
    contact_id = create_response.json()["data"]["id"]
    
    get_response = client.get(f"/api/v1/sms/contacts/{contact_id}", headers=auth_headers)
    assert get_response.status_code == 200
    
    update_response = client.put(
        f"/api/v1/sms/contacts/{contact_id}",
        json={"identity": "紧急接收人"},
        headers=write_headers
    )
    assert update_response.status_code == 200
    
    delete_response = client.delete(f"/api/v1/sms/contacts/{contact_id}", headers=write_headers)
    assert delete_response.status_code == 200
