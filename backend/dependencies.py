"""FastAPI 依赖注入：get_db, get_current_user。"""

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db as _get_db
from backend.services.auth import get_user_by_id


# 重用 database 模块的 get_db 作为 FastAPI 依赖
get_db = Depends(_get_db)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(_get_db),  # type: ignore[assignment]
):
    """从中间件注入的 current_user_id 加载 User 对象。
    未登录返回 401。
    """
    user_id: int | None = getattr(request.state, "current_user_id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(_get_db),  # type: ignore[assignment]
):
    """可选的当前用户 —— 未登录返回 None，不报错。"""
    user_id: int | None = getattr(request.state, "current_user_id", None)
    if user_id is None:
        return None
    return await get_user_by_id(db, user_id)
