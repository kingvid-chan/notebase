"""笔记模块测试：CRUD + 权限隔离 + 全文搜索。"""

import pytest
from backend.config import settings

API = f"{settings.BASE_PATH}/api/notes"


async def _login(client, username="alice", password="demo123"):
    await client.post(
        f"{settings.BASE_PATH}/api/auth/login",
        json={"username": username, "password": password},
    )


@pytest.mark.asyncio
async def test_create_note(client, user_alice):
    await _login(client)
    resp = await client.post(
        f"{API}",
        json={"title": "测试笔记", "content_markdown": "# Hello\n\nThis is a test."},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["note"]["title"] == "测试笔记"
    assert data["note"]["content_markdown"] == "# Hello\n\nThis is a test."
    # HTML should be auto-rendered
    assert "<h1>Hello</h1>" in data["note"]["content_html"]


@pytest.mark.asyncio
async def test_list_notes(client, user_alice):
    await _login(client)
    # Create a couple notes
    await client.post(f"{API}", json={"title": "Note 1", "content_markdown": "one"})
    await client.post(f"{API}", json={"title": "Note 2", "content_markdown": "two"})

    resp = await client.get(f"{API}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["notes"]) == 2


@pytest.mark.asyncio
async def test_get_note(client, user_alice):
    await _login(client)
    create_resp = await client.post(
        f"{API}", json={"title": "My Note", "content_markdown": "content"}
    )
    note_id = create_resp.json()["note"]["id"]

    resp = await client.get(f"{API}/{note_id}")
    assert resp.status_code == 200
    assert resp.json()["note"]["title"] == "My Note"


@pytest.mark.asyncio
async def test_update_note(client, user_alice):
    await _login(client)
    create_resp = await client.post(
        f"{API}", json={"title": "Original", "content_markdown": "original"}
    )
    note_id = create_resp.json()["note"]["id"]

    resp = await client.put(
        f"{API}/{note_id}",
        json={"title": "Updated", "content_markdown": "**updated**"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["note"]["title"] == "Updated"
    assert "<strong>updated</strong>" in data["note"]["content_html"]


@pytest.mark.asyncio
async def test_delete_note(client, user_alice):
    await _login(client)
    create_resp = await client.post(
        f"{API}", json={"title": "To Delete", "content_markdown": "bye"}
    )
    note_id = create_resp.json()["note"]["id"]

    resp = await client.delete(f"{API}/{note_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify deleted
    resp = await client.get(f"{API}/{note_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_others_note(client, user_alice, user_bob):
    # Alice creates a note
    await _login(client, "alice", "demo123")
    create_resp = await client.post(
        f"{API}", json={"title": "Alice Private", "content_markdown": "secret"}
    )
    note_id = create_resp.json()["note"]["id"]

    # Bob logs in and tries to access Alice's note
    await _login(client, "bob", "demo456")
    resp = await client.get(f"{API}/{note_id}")
    assert resp.status_code == 404  # Not found for Bob


@pytest.mark.asyncio
async def test_search_notes(client, user_alice):
    await _login(client)
    await client.post(
        f"{API}", json={"title": "Python Guide", "content_markdown": "learn python programming"}
    )
    await client.post(
        f"{API}", json={"title": "JavaScript Tips", "content_markdown": "JS tutorials"}
    )
    await client.post(
        f"{API}", json={"title": "Other", "content_markdown": "unrelated stuff"}
    )

    resp = await client.get(f"{API}?q=python")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    titles = [n["title"] for n in data["notes"]]
    assert "Python Guide" in titles
    assert "JavaScript Tips" not in titles


@pytest.mark.asyncio
async def test_filter_by_tag(client, user_alice):
    await _login(client)
    # Create a note with tags
    resp = await client.post(
        f"{API}",
        json={
            "title": "Tagged Note",
            "content_markdown": "content",
            "tag_ids": [],
        },
    )
    assert resp.status_code == 201
    note_id = resp.json()["note"]["id"]

    # Create a label and add to note
    label_resp = await client.post(
        f"{settings.BASE_PATH}/api/tags",
        json={"name": "urgent"},
    )
    label_id = label_resp.json()["id"]
    await client.post(f"{API}/{note_id}/tags", json={"tag_id": label_id})

    # Filter
    resp = await client.get(f"{API}?tag=urgent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
