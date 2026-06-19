"""Session 工具：签名/验证 session Cookie (itsdangerous)。"""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.config import settings

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="session")


def sign_session(user_id: int) -> str:
    """签名用户 ID，返回 token 字符串。"""
    return _serializer.dumps(str(user_id))  # type: ignore[no-any-return]


def unsign_session(token: str) -> int | None:
    """验证 token，返回 user_id 或 None。"""
    try:
        user_id = _serializer.loads(token, max_age=settings.SESSION_MAX_AGE)
        return int(user_id)
    except (SignatureExpired, BadSignature, ValueError):
        return None
