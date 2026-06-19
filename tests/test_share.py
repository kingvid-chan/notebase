"""分享模块测试：生成链接、公开访问、撤销、权限校验。"""

import pytest
from backend.config import settings

NOTES_API = f"{settings.BASE_PATH}/api/notes"
API = f"{settings.BASE_PATH}/api"


async def _login(client, username="alice", password="demo123"):
    await client.post(
        f"{settings.BASE_PATH}/api/auth/login",
        json={"username": username, "password": password},
    )


async def _create_note(client, title="Share Test Note", content="# Shared"):
    resp = await client.post(
        f"{NOTES_API}",
        json={"title": title, "content_markdown": content},
    )
    assert resp.status_code == 201
    return resp.json()["note"]["id"]


# ---------------------------------------------------------------------------
# 生成分享链接
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_share_link(client, user_alice):
    await _login(client)
    note_id = await _create_note(client)

    resp = await client.post(f"{API}/notes/{note_id}/share")
    assert resp.status_code == 201
    data = resp.json()
    assert data["note_id"] == note_id
    assert "token" in data
    assert len(data["token"]) > 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_share_link_for_nonexistent_note(client, user_alice):
    await _login(client)
    resp = await client.post(f"{API}/notes/99999/share")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_share_link_unauthenticated(client):
    resp = await client.post(f"{API}/notes/1/share")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 列出分享链接
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_share_links(client, user_alice):
    await _login(client)
    note_id = await _create_note(client)

    # Create two share links
    await client.post(f"{API}/notes/{note_id}/share")
    await client.post(f"{API}/notes/{note_id}/share")

    resp = await client.get(f"{API}/notes/{note_id}/shares")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["share_links"]) == 2


@pytest.mark.asyncio
async def test_list_share_links_empty(client, user_alice):
    await _login(client)
    note_id = await _create_note(client)

    resp = await client.get(f"{API}/notes/{note_id}/shares")
    assert resp.status_code == 200
    data = resp.json()
    assert data["share_links"] == []


# ---------------------------------------------------------------------------
# 公开访问分享页面
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_access_share_page(client, user_alice):
    await _login(client)
    note_id = await _create_note(client, "Public Note", "# Hello World")

    share_resp = await client.post(f"{API}/notes/{note_id}/share")
    token = share_resp.json()["token"]

    # Access without authentication
    resp = await client.get(f"{settings.BASE_PATH}/share/{token}")
    assert resp.status_code == 200
    # Should be an HTML page
    assert "text/html" in resp.headers.get("content-type", "")
    # Should contain the note title
    assert "Public Note" in resp.text


@pytest.mark.asyncio
async def test_share_page_invalid_token(client):
    resp = await client.get(f"{settings.BASE_PATH}/share/invalid-token-xyz")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 撤销分享链接
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_share_link(client, user_alice):
    await _login(client)
    note_id = await _create_note(client)

    share_resp = await client.post(f"{API}/notes/{note_id}/share")
    share_id = share_resp.json()["id"]
    token = share_resp.json()["token"]

    # Revoke
    resp = await client.delete(f"{API}/notes/{note_id}/share/{share_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Token should no longer work
    resp = await client.get(f"{settings.BASE_PATH}/share/{token}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_revoke_nonexistent_share(client, user_alice):
    await _login(client)
    note_id = await _create_note(client)

    resp = await client.delete(f"{API}/notes/{note_id}/share/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 权限校验：不能操作他人的笔记分享
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_share_others_note(client, user_alice, user_bob):
    # Alice creates note
    await _login(client, "alice", "demo123")
    note_id = await _create_note(client, "Alice Note")

    # Bob tries to create share for Alice's note
    await _login(client, "bob", "demo456")
    resp = await client.post(f"{API}/notes/{note_id}/share")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_list_shares_of_others_note(client, user_alice, user_bob):
    # Alice creates note and share
    await _login(client, "alice", "demo123")
    note_id = await _create_note(client, "Alice Note")
    await client.post(f"{API}/notes/{note_id}/share")

    # Bob tries to list shares
    await _login(client, "bob", "demo456")
    resp = await client.get(f"{API}/notes/{note_id}/shares")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_revoke_others_share(client, user_alice, user_bob):
    # Alice creates note and share
    await _login(client, "alice", "demo123")
    note_id = await _create_note(client, "Alice Note")
    share_resp = await client.post(f"{API}/notes/{note_id}/share")
    share_id = share_resp.json()["id"]

    # Bob tries to revoke
    await _login(client, "bob", "demo456")
    resp = await client.delete(f"{API}/notes/{note_id}/share/{share_id}")
    assert resp.status_code == 404
