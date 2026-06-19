"""页面路由：SPA 外壳 + 公开分享阅读页。"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from backend.config import settings
from backend.database import get_db
from backend.services.share import get_note_by_token

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def spa_index(request: Request):
    """SPA 入口页面，注入 base_path 和版本令牌。"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "base_path": settings.BASE_PATH,
            "version": settings.VERSION,
        },
    )


@router.get("/share/{token}", response_class=HTMLResponse)
async def shared_note_page(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """公开分享页面 —— 无需登录，只读渲染。"""
    note = await get_note_by_token(db, token)
    if not note:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")

    # 提取标题中的纯文本（去除 Markdown 语法）作为页面标题
    title = note.title

    return templates.TemplateResponse(
        "shared-note.html",
        {
            "request": request,
            "base_path": settings.BASE_PATH,
            "version": settings.VERSION,
            "note": note,
            "page_title": title,
        },
    )
