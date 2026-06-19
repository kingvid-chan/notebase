"""FastAPI 中间件：Session 解析 + Cache-Control 注入。"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.services.session import unsign_session

COOKIE_NAME = "session"


class SessionMiddleware(BaseHTTPMiddleware):
    """从 Cookie 解析当前用户 ID，写入 request.state.current_user_id。

    该中间件不拦截请求 —— 无论是否登录都放行。认证要求由各路由通过
    get_current_user 依赖注入自行决定。
    """

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get(COOKIE_NAME)
        user_id = None
        if token:
            user_id = unsign_session(token)
        request.state.current_user_id = user_id
        response = await call_next(request)
        return response  # type: ignore[no-any-return]


class CacheControlMiddleware(BaseHTTPMiddleware):
    """为 HTML 响应添加 Cache-Control: no-cache 头。

    Hermes 验收要求：HTML 文档必须由服务器下发真实的 HTTP Cache-Control 响应头，
    不能使用 <meta> 标签代替。
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-cache"
        elif "application/json" in content_type:
            response.headers["Cache-Control"] = "no-store"
        return response  # type: ignore[no-any-return]
