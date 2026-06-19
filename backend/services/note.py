"""笔记服务：CRUD + FTS5 全文搜索。"""

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Note, NoteTag, Tag
from backend.services.markdown import MarkdownRenderer

_renderer = MarkdownRenderer()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_note(
    db: AsyncSession,
    user_id: int,
    title: str,
    content_markdown: str,
    tag_ids: list[int] | None = None,
) -> Note:
    """创建笔记，服务端渲染 HTML。"""
    content_html = _renderer.render(content_markdown)
    note = Note(
        user_id=user_id,
        title=title,
        content_markdown=content_markdown,
        content_html=content_html,
    )
    db.add(note)
    await db.flush()

    if tag_ids:
        for tid in tag_ids:
            db.add(NoteTag(note_id=note.id, tag_id=tid))
        await db.flush()

    await db.refresh(note)
    return note


async def get_note(db: AsyncSession, note_id: int, user_id: int) -> Note | None:
    """获取单条笔记（仅所有者）。"""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_note_tags(db: AsyncSession, note_id: int) -> list[Tag]:
    """获取笔记的标签列表。"""
    result = await db.execute(
        select(Tag)
        .join(NoteTag, NoteTag.tag_id == Tag.id)
        .where(NoteTag.note_id == note_id)
    )
    return list(result.scalars().all())


async def update_note(
    db: AsyncSession,
    note: Note,
    *,
    title: str | None = None,
    content_markdown: str | None = None,
    is_public: int | None = None,
) -> Note:
    """更新笔记字段，若内容变更则重新渲染 HTML。"""
    if title is not None:
        note.title = title
    if content_markdown is not None:
        note.content_markdown = content_markdown
        note.content_html = _renderer.render(content_markdown)
    if is_public is not None:
        note.is_public = is_public
    note.updated_at = datetime.utcnow().isoformat()
    await db.flush()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note: Note) -> None:
    """删除笔记（级联删除关联）。"""
    await db.delete(note)
    await db.flush()


# ---------------------------------------------------------------------------
# 列表 & 搜索
# ---------------------------------------------------------------------------


async def list_notes(
    db: AsyncSession,
    user_id: int,
    *,
    tag: str | None = None,
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Note], int]:
    """列出用户笔记，支持按标签筛选和全文搜索。"""
    offset = (page - 1) * limit

    if q:
        # FTS5 全文搜索
        return await _search_notes(db, user_id, q, tag, offset, limit)

    # 基础查询
    query = select(Note).where(Note.user_id == user_id)
    count_q = select(func.count()).select_from(Note).where(Note.user_id == user_id)

    if tag:
        query = (
            query.join(NoteTag, NoteTag.note_id == Note.id)
            .join(Tag, Tag.id == NoteTag.tag_id)
            .where(Tag.name == tag, Tag.user_id == user_id)
        )
        count_q = (
            count_q.join(NoteTag, NoteTag.note_id == Note.id)
            .join(Tag, Tag.id == NoteTag.tag_id)
            .where(Tag.name == tag, Tag.user_id == user_id)
        )

    total = (await db.execute(count_q)).scalar_one()
    rows = (
        await db.execute(query.order_by(Note.updated_at.desc()).offset(offset).limit(limit))
    ).scalars().all()

    return list(rows), total


async def _search_notes(
    db: AsyncSession,
    user_id: int,
    q: str,
    tag: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Note], int]:
    """FTS5 全文搜索。"""
    # 转义 FTS5 特殊字符并构造 MATCH 查询
    safe_q = q.replace('"', '""')
    match_expr = f'notes_fts MATCH :match'

    params = {"match": f'"{safe_q}"', "uid": user_id, "limit": limit, "offset": offset}

    if tag:
        count_sql = text(
            "SELECT COUNT(*) FROM notes "
            "JOIN notes_fts ON notes.id = notes_fts.rowid "
            "JOIN note_tags ON note_tags.note_id = notes.id "
            "JOIN tags ON tags.id = note_tags.tag_id "
            f"WHERE {match_expr} AND notes.user_id = :uid "
            "AND tags.name = :tag AND tags.user_id = :uid"
        )
        params["tag"] = tag
        total = (await db.execute(count_sql, params)).scalar_one()

        sql = text(
            "SELECT notes.* FROM notes "
            "JOIN notes_fts ON notes.id = notes_fts.rowid "
            "JOIN note_tags ON note_tags.note_id = notes.id "
            "JOIN tags ON tags.id = note_tags.tag_id "
            f"WHERE {match_expr} AND notes.user_id = :uid "
            "AND tags.name = :tag AND tags.user_id = :uid "
            "ORDER BY rank, notes.updated_at DESC "
            "LIMIT :limit OFFSET :offset"
        )
    else:
        count_sql = text(
            "SELECT COUNT(*) FROM notes "
            "JOIN notes_fts ON notes.id = notes_fts.rowid "
            f"WHERE {match_expr} AND notes.user_id = :uid"
        )
        total = (await db.execute(count_sql, params)).scalar_one()

        sql = text(
            "SELECT notes.* FROM notes "
            "JOIN notes_fts ON notes.id = notes_fts.rowid "
            f"WHERE {match_expr} AND notes.user_id = :uid "
            "ORDER BY rank, notes.updated_at DESC "
            "LIMIT :limit OFFSET :offset"
        )

    rows = (await db.execute(sql, params)).all()
    notes = [
        Note(
            id=row[0],
            user_id=row[1],
            title=row[2],
            content_markdown=row[3],
            content_html=row[4],
            is_public=row[5],
            created_at=row[6],
            updated_at=row[7],
        )
        for row in rows
    ]
    return notes, total
