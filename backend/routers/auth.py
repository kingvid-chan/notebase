"""认证路由：注册 / 登录 / 登出 / 当前用户。"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.middleware import COOKIE_NAME
from backend.models import User
from backend.schemas import AuthResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from backend.services.auth import login_user, register_user

router = APIRouter()

SAME_SITE = "lax"  # 非 HTTPS 环境使用 Lax

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
        samesite=SAME_SITE,
        secure=False,  # 演示环境无 HTTPS
        path=settings.BASE_PATH,
    )


def _clear_session_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path=settings.BASE_PATH)


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """注册新用户，自动登录。"""
    try:
        user, token = await register_user(db, body.username, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    _set_session_cookie(response, token)
    return AuthResponse(user=UserResponse.model_validate(user), session_token=token)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """登录。"""
    try:
        user, token = await login_user(db, body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    _set_session_cookie(response, token)
    return AuthResponse(user=UserResponse.model_validate(user), session_token=token)


@router.post("/logout")
async def logout(response: Response):
    """登出。"""
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """当前登录用户信息。"""
    return UserResponse.model_validate(current_user)
