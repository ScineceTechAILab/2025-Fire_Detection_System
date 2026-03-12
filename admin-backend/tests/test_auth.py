from fastapi.testclient import TestClient
from app.main import app
from app.core.storage import get_storage_manager
import bcrypt


client = TestClient(app)


def setup_module(_):
    storage = get_storage_manager()
    hashed = bcrypt.hashpw(b"Qq12345678", bcrypt.gensalt()).decode()
    storage.write("admin.json", {
        "user": "admin",
        "password": hashed
    })


def test_login_success_and_me():
    resp = client.post("/api/v1/auth/login", json={"user": "admin", "password": "Qq12345678"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    token = data["token"]
    csrf = data["csrf_token"]
    cookies = resp.cookies
    assert cookies.get("csrf_token") == csrf

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"] == "admin"


def test_protected_without_token():
    import os
    resp = client.get("/api/v1/system/params")
    if os.getenv("ADMIN_DISABLE_AUTH") == "1":
        assert resp.status_code == 200
    else:
        assert resp.status_code in (401, 403)


def test_login_fail():
    r = client.post("/api/v1/auth/login", json={"user": "admin", "password": "bad"})
    assert r.status_code == 401
