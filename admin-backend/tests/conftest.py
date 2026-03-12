import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.storage import get_storage_manager


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth_context(client: TestClient):
    storage = get_storage_manager()
    hashed = bcrypt.hashpw(b"Qq12345678", bcrypt.gensalt()).decode()
    storage.write("admin.json", {"user": "admin", "password": hashed})
    resp = client.post("/api/v1/auth/login", json={"user": "admin", "password": "Qq12345678"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    return data["token"], data["csrf_token"]


@pytest.fixture()
def auth_headers(auth_context):
    token, _csrf = auth_context
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def write_headers(auth_context):
    token, csrf = auth_context
    return {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}

