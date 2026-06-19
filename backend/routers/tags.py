"""标签路由：CRUD。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User
from backend.schemas import TagCreateRequest, TagListResponse, TagResponse
from backend.services import tag as tag_service

router = APIRouter()


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(
    body: TagCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建标签。"""
    try:
        tag = await tag_service.create_tag(db, current_user.id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return TagResponse.model_validate(tag)


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的所有标签。"""
    tags = await tag_service.list_tags(db, current_user.id)
    return TagListResponse(tags=[TagResponse.model_validate(t) for t in tags])


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除标签。"""
    ok = await tag_service.delete_tag(db, tag_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="标签不存在")
    return {"ok": True}
