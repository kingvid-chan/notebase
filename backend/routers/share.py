"""分享路由：生成/撤销分享链接、公开访问。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User
from backend.schemas import (
    ShareLinkCreateRequest,
    ShareLinkListResponse,
    ShareLinkResponse,
)
from backend.services import note as note_service
from backend.services import share as share_service

router = APIRouter()


# ---------------------------------------------------------------------------
# 分享链接管理（需登录）
# ---------------------------------------------------------------------------


@router.post("/notes/{note_id}/share", response_model=ShareLinkResponse, status_code=201)
async def create_share(
    note_id: int,
    body: ShareLinkCreateRequest = ShareLinkCreateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """为笔记生成分享链接。"""
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    link = await share_service.create_share_link(
        db, note_id, expires_at=body.expires_at
    )
    return ShareLinkResponse.model_validate(link)


@router.get("/notes/{note_id}/shares", response_model=ShareLinkListResponse)
async def list_shares(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取笔记的所有分享链接。"""
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    links = await share_service.get_share_links_for_note(db, note_id)
    return ShareLinkListResponse(
        share_links=[ShareLinkResponse.model_validate(l) for l in links]
    )


@router.delete("/notes/{note_id}/share/{share_id}")
async def revoke_share(
    note_id: int,
    share_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤销分享链接。"""
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    ok = await share_service.delete_share_link(db, share_id)
    if not ok:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    return {"ok": True}
