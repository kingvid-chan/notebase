"""标签模块测试：CRUD + 笔记关联 + 用户隔离。"""

import pytest
from backend.config import settings

API = f"{settings.BASE_PATH}/api/tags"
NOTES_API = f"{settings.BASE_PATH}/api/notes"


async def _login(client, username="alice", password="demo123"):
    await client.post(
        f"{settings.BASE_PATH}/api/auth/login",
        json={"username": username, "password": password},
    )


@pytest.mark.asyncio
async def test_create_tag(client, user_alice):
    await _login(client)
    resp = await client.post(f"{API}", json={"name": "programming"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "programming"
    assert data["user_id"] == user_alice.id


@pytest.mark.asyncio
async def test_create_duplicate_tag(client, user_alice):
    await _login(client)
    await client.post(f"{API}", json={"name": "test"})
    resp = await client.post(f"{API}", json={"name": "test"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_tags(client, user_alice):
    await _login(client)
    await client.post(f"{API}", json={"name": "a"})
    await client.post(f"{API}", json={"name": "b"})

    resp = await client.get(f"{API}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tags"]) == 2


@pytest.mark.asyncio
async def test_delete_tag(client, user_alice):
    await _login(client)
    create_resp = await client.post(f"{API}", json={"name": "todelete"})
    tag_id = create_resp.json()["id"]

    resp = await client.delete(f"{API}/{tag_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify deleted
    resp = await client.get(f"{API}")
    assert all(t["id"] != tag_id for t in resp.json()["tags"])


@pytest.mark.asyncio
async def test_add_tag_to_note(client, user_alice):
    await _login(client)
    # Create note
    note_resp = await client.post(
        f"{NOTES_API}", json={"title": "Note", "content_markdown": "text"}
    )
    note_id = note_resp.json()["note"]["id"]

    # Create tag
    tag_resp = await client.post(f"{API}", json={"name": "work"})
    tag_id = tag_resp.json()["id"]

    # Add tag to note
    resp = await client.post(
        f"{NOTES_API}/{note_id}/tags", json={"tag_id": tag_id}
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify: note detail includes tags
    detail_resp = await client.get(f"{NOTES_API}/{note_id}")
    assert len(detail_resp.json()["tags"]) == 1
    assert detail_resp.json()["tags"][0]["name"] == "work"


@pytest.mark.asyncio
async def test_remove_tag_from_note(client, user_alice):
    await _login(client)
    # Setup
    note_resp = await client.post(
        f"{NOTES_API}", json={"title": "Note", "content_markdown": "text"}
    )
    note_id = note_resp.json()["note"]["id"]
    tag_resp = await client.post(f"{API}", json={"name": "temp"})
    tag_id = tag_resp.json()["id"]
    await client.post(f"{NOTES_API}/{note_id}/tags", json={"tag_id": tag_id})

    # Remove
    resp = await client.delete(f"{NOTES_API}/{note_id}/tags/{tag_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify removed
    detail_resp = await client.get(f"{NOTES_API}/{note_id}")
    assert len(detail_resp.json()["tags"]) == 0


@pytest.mark.asyncio
async def test_tag_isolation(client, user_alice, user_bob):
    await _login(client, "alice", "demo123")
    await client.post(f"{API}", json={"name": "alice_tag"})

    await _login(client, "bob", "demo456")
    resp = await client.get(f"{API}")
    # Bob should not see Alice's tags
    names = [t["name"] for t in resp.json()["tags"]]
    assert "alice_tag" not in names
