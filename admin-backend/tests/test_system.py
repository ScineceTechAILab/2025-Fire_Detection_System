"""
类级注释：系统管理模块测试
"""
import pytest
import threading
import time
import os
import shutil
from pathlib import Path

from app.main import app
from app.core.storage import get_storage_manager

TEST_CONFIG_DIR = Path("test_config_system")


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


def test_reload_config(client, write_headers):
    """
    函数级注释：测试配置热加载
    """
    response = client.post("/api/v1/system/reload", headers=write_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "配置重新加载成功" in data["msg"]


def test_health_check(client):
    """
    函数级注释：测试健康检查
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root(client):
    """
    函数级注释：测试根路径
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "running"


def test_concurrent_reload(client, write_headers):
    """
    函数级注释：测试并发reload场景
    """
    results = []
    errors = []
    
    def reload_task():
        try:
            response = client.post("/api/v1/system/reload", headers=write_headers)
            results.append(response.status_code)
        except Exception as e:
            errors.append(str(e))
    
    threads = []
    for _ in range(10):
        t = threading.Thread(target=reload_task)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0
    assert all(code == 200 for code in results)


def test_file_locking():
    """
    函数级注释：测试文件锁防止并发写入损坏
    """
    storage = get_storage_manager()
    
    results = []
    
    def write_task():
        try:
            for i in range(10):
                data = storage.read("feishu.json")
                data["group_chat_id"] = f"test_{i}"
                storage.write("feishu.json", data)
            results.append(True)
        except Exception:
            results.append(False)
    
    threads = []
    for _ in range(5):
        t = threading.Thread(target=write_task)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert all(results)
