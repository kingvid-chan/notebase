"""标签服务：CRUD + 笔记关联管理。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import NoteTag, Tag


async def create_tag(db: AsyncSession, user_id: int, name: str) -> Tag:
    """创建标签（同一用户下标签名唯一）。"""
    existing = await db.execute(
        select(Tag).where(Tag.user_id == user_id, Tag.name == name)
    )
    if existing.scalar_one_or_none():
        raise ValueError("标签已存在")

    tag = Tag(name=name, user_id=user_id)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def list_tags(db: AsyncSession, user_id: int) -> list[Tag]:
    """获取用户所有标签。"""
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
    )
    return list(result.scalars().all())


async def delete_tag(db: AsyncSession, tag_id: int, user_id: int) -> bool:
    """删除标签（自动解除所有关联）。"""
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    tag = result.scalar_one_or_none()
    if not tag:
        return False
    await db.delete(tag)
    await db.flush()
    return True


async def add_tag_to_note(db: AsyncSession, note_id: int, tag_id: int) -> bool:
    """为笔记添加标签。"""
    existing = await db.execute(
        select(NoteTag).where(
            NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
        )
    )
    if existing.scalar_one_or_none():
        return False  # 已关联，幂等

    db.add(NoteTag(note_id=note_id, tag_id=tag_id))
    await db.flush()
    return True


async def remove_tag_from_note(db: AsyncSession, note_id: int, tag_id: int) -> bool:
    """移除笔记标签关联。"""
    result = await db.execute(
        select(NoteTag).where(
            NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
        )
    )
    nt = result.scalar_one_or_none()
    if not nt:
        return False
    await db.delete(nt)
    await db.flush()
    return True
