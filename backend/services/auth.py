"""认证服务：注册、登录、登出。"""

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User
from backend.services.session import sign_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def register_user(
    db: AsyncSession, username: str, email: str, password: str
) -> tuple[User, str]:
    """注册新用户，返回 (user, session_token)。"""
    # 检查唯一性
    existing = await db.execute(
        select(User).where((User.username == username) | (User.email == email))
    )
    if existing.scalar_one_or_none():
        raise ValueError("用户名或邮箱已被注册")

    user = User(
        username=username,
        email=email,
        password_hash=pwd_context.hash(password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = sign_session(user.id)
    return user, token


async def login_user(
    db: AsyncSession, username: str, password: str
) -> tuple[User, str]:
    """登录验证，返回 (user, session_token)。"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(password, user.password_hash):
        raise ValueError("用户名或密码错误")

    token = sign_session(user.id)
    return user, token


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """按 ID 查询用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
