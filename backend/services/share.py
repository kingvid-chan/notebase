"""分享服务：链接生成、验证、撤销。"""

import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Note, ShareLink


def generate_token() -> str:
    """生成 URL-safe 随机 token (192 bits 熵)。"""
    return secrets.token_urlsafe(32)


async def create_share_link(
    db: AsyncSession, note_id: int, expires_at: str | None = None
) -> ShareLink:
    """为笔记创建分享链接。"""
    link = ShareLink(
        note_id=note_id,
        token=generate_token(),
        expires_at=expires_at,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


async def get_share_links_for_note(
    db: AsyncSession, note_id: int
) -> list[ShareLink]:
    """获取笔记的所有分享链接。"""
    result = await db.execute(
        select(ShareLink).where(ShareLink.note_id == note_id)
    )
    return list(result.scalars().all())


async def delete_share_link(
    db: AsyncSession, share_id: int
) -> bool:
    """撤销分享链接。"""
    result = await db.execute(
        select(ShareLink).where(ShareLink.id == share_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        return False
    await db.delete(link)
    await db.flush()
    return True


async def get_note_by_token(
    db: AsyncSession, token: str
) -> Note | None:
    """通过分享 token 获取笔记（含过期校验）。"""
    result = await db.execute(
        select(ShareLink).where(ShareLink.token == token)
    )
    link = result.scalar_one_or_none()
    if not link:
        return None

    # 校验过期
    if link.expires_at:
        try:
            expires = datetime.fromisoformat(link.expires_at)
            if datetime.utcnow() > expires:
                return None
        except (ValueError, TypeError):
            pass

    # 加载笔记
    result = await db.execute(
        select(Note).where(Note.id == link.note_id)
    )
    return result.scalar_one_or_none()
