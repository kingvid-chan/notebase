"""Pytest fixtures: async client, test database, demo users."""

import os
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.database import Base, get_db
from backend.models import Note, NoteTag, ShareLink, Tag, User
from backend.app import create_app

# Use in-memory database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite://"

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


async def _override_get_db():
    """Override get_db to use test database."""
    async with AsyncSession(_test_engine, expire_on_commit=False) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def setup_database():
    """Create all tables + FTS5 + triggers before each test, drop after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5("
                "    title, content_markdown, content='notes', content_rowid='id')"
            )
        )
        # FTS5 sync triggers — keep index in sync with notes table
        await conn.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN "
                "  INSERT INTO notes_fts(rowid, title, content_markdown) "
                "  VALUES (new.id, new.title, new.content_markdown); "
                "END"
            )
        )
        await conn.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN "
                "  INSERT INTO notes_fts(notes_fts, rowid, title, content_markdown) "
                "  VALUES ('delete', old.id, old.title, old.content_markdown); "
                "END"
            )
        )
        await conn.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN "
                "  INSERT INTO notes_fts(notes_fts, rowid, title, content_markdown) "
                "  VALUES ('delete', old.id, old.title, old.content_markdown); "
                "  INSERT INTO notes_fts(rowid, title, content_markdown) "
                "  VALUES (new.id, new.title, new.content_markdown); "
                "END"
            )
        )
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS notes_fts"))


@pytest_asyncio.fixture(loop_scope="function")
async def client():
    """Async HTTP test client."""
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="function")
async def db():
    """Raw async session for direct DB access."""
    async with AsyncSession(_test_engine, expire_on_commit=False) as session:
        yield session


# ---------------------------------------------------------------------------
# Demo user fixtures
# ---------------------------------------------------------------------------


async def _create_user(session: AsyncSession, username: str, password: str):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash=pwd_context.hash(password),
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture(loop_scope="function")
async def user_alice(client, db):
    """Create alice user."""
    user = await _create_user(db, "alice", "demo123")
    await db.commit()
    return user


@pytest_asyncio.fixture(loop_scope="function")
async def user_bob(client, db):
    """Create bob user."""
    user = await _create_user(db, "bob", "demo456")
    await db.commit()
    return user


@pytest_asyncio.fixture(loop_scope="function")
async def logged_in_client(client, user_alice):
    """Client logged in as alice."""
    resp = await client.post(
        f"{settings.BASE_PATH}/api/auth/login",
        json={"username": "alice", "password": "demo123"},
    )
    assert resp.status_code == 200
    # Return client (cookies are automatically handled by httpx)
    return client
