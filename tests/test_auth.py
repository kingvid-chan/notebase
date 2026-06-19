"""认证模块测试：注册 / 登录 / 登出 / 权限拦截。"""

import pytest
from backend.config import settings

API = f"{settings.BASE_PATH}/api/auth"


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post(
        f"{API}/register",
        json={"username": "newuser", "email": "new@test.com", "password": "pass1234"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["username"] == "newuser"
    assert data["user"]["email"] == "new@test.com"
    assert "session_token" in data
    assert "session" in resp.cookies


@pytest.mark.asyncio
async def test_register_duplicate(client, user_alice):
    resp = await client.post(
        f"{API}/register",
        json={"username": "alice", "email": "alice@test.com", "password": "pass1234"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client, user_alice):
    resp = await client.post(
        f"{API}/login",
        json={"username": "alice", "password": "demo123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "alice"
    assert "session" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client, user_alice):
    resp = await client.post(
        f"{API}/login",
        json={"username": "alice", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post(
        f"{API}/login",
        json={"username": "ghost", "password": "whatever"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, user_alice):
    # Login first
    await client.post(
        f"{API}/login",
        json={"username": "alice", "password": "demo123"},
    )
    resp = await client.post(f"{API}/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Cookie should be cleared (httpx may return None when cookie is deleted with max-age=0)
    assert resp.cookies.get("session") in ('""', "", None)


@pytest.mark.asyncio
async def test_me_authenticated(client, user_alice):
    await client.post(
        f"{API}/login",
        json={"username": "alice", "password": "demo123"},
    )
    resp = await client.get(f"{API}/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get(f"{API}/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cache_control_header_html(client):
    """Verifies HTML responses carry Cache-Control: no-cache header."""
    resp = await client.get(f"{settings.BASE_PATH}/")
    assert resp.status_code == 200
    # The middleware sets Cache-Control on HTML responses
    cc = resp.headers.get("cache-control", "")
    assert "no-cache" in cc
