"""笔记路由：CRUD、列表、搜索。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import Note, User
from backend.schemas.note import (
    NoteCreateRequest,
    NoteDetailResponse,
    NoteListResponse,
    NoteResponse,
    NoteUpdateRequest,
)
from backend.schemas.tag import TagResponse
from backend.services import note as note_service

router = APIRouter()


# ---------------------------------------------------------------------------
# 列表 & 搜索
# ---------------------------------------------------------------------------


@router.get("", response_model=NoteListResponse)
async def list_notes(
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None, description="FTS5 全文搜索关键词"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """笔记列表，支持标签筛选和全文搜索。"""
    notes, total = await note_service.list_notes(
        db, current_user.id, tag=tag, q=q, page=page, limit=limit
    )
    return NoteListResponse(
        notes=[NoteResponse.model_validate(n) for n in notes],
        total=total,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=NoteDetailResponse, status_code=201)
async def create_note(
    body: NoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建笔记。"""
    note = await note_service.create_note(
        db, current_user.id, body.title, body.content_markdown, body.tag_ids
    )
    tags = await note_service.get_note_tags(db, note.id)
    return NoteDetailResponse(
        note=NoteResponse.model_validate(note),
        tags=[TagResponse.model_validate(t) for t in tags],
    )


@router.get("/{note_id}", response_model=NoteDetailResponse)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单条笔记详情。"""
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    tags = await note_service.get_note_tags(db, note_id)
    return NoteDetailResponse(
        note=NoteResponse.model_validate(note),
        tags=[TagResponse.model_validate(t) for t in tags],
    )


@router.put("/{note_id}", response_model=NoteDetailResponse)
async def update_note(
    note_id: int,
    body: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新笔记。"""
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    kwargs = {}
    if body.title is not None:
        kwargs["title"] = body.title
    if body.content_markdown is not None:
        kwargs["content_markdown"] = body.content_markdown
    if body.is_public is not None:
        kwargs["is_public"] = 1 if body.is_public else 0

    note = await note_service.update_note(db, note, **kwargs)
    tags = await note_service.get_note_tags(db, note_id)
    return NoteDetailResponse(
        note=NoteResponse.model_validate(note),
        tags=[TagResponse.model_validate(t) for t in tags],
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除笔记。"""
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    await note_service.delete_note(db, note)
    return {"ok": True}
