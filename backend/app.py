"""FastAPI 应用入口 —— app 工厂、路由挂载、中间件、静态文件。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import settings

# ---------------------------------------------------------------------------
# app 工厂
# ---------------------------------------------------------------------------

_root = Path(__file__).resolve().parent.parent  # 项目根目录


def create_app() -> FastAPI:
    app = FastAPI(
        title="notebase",
        version=settings.VERSION,
        docs_url=f"{settings.BASE_PATH}/docs",
        openapi_url=f"{settings.BASE_PATH}/openapi.json",
    )

    # 中间件需在 router 之前注册
    from backend.middleware import SessionMiddleware, CacheControlMiddleware

    app.add_middleware(CacheControlMiddleware)
    app.add_middleware(SessionMiddleware)

    # API 路由
    from backend.routers.auth import router as auth_router
    from backend.routers.notes import router as notes_router
    from backend.routers.tags import router as tags_router
    from backend.routers.share import router as share_router

    api_prefix = f"{settings.BASE_PATH}/api"
    app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["auth"])
    app.include_router(notes_router, prefix=f"{api_prefix}/notes", tags=["notes"])
    app.include_router(tags_router, prefix=f"{api_prefix}/tags", tags=["tags"])
    app.include_router(share_router, prefix=api_prefix, tags=["share"])

    # 前端 SPA 入口 & 公开分享页 (Jinja2)
    from backend.routers.pages import router as pages_router

    app.include_router(pages_router, prefix=settings.BASE_PATH)

    # 静态资源 (CSS/JS) —— mounted under BASE_PATH
    frontend_dir = _root / "frontend"
    if frontend_dir.is_dir():
        app.mount(
            f"{settings.BASE_PATH}/static",
            StaticFiles(directory=str(frontend_dir)),
            name="frontend",
        )

    # 健康检查
    @app.get(f"{settings.BASE_PATH}/health")
    async def health():
        return {"ok": True, "version": settings.VERSION}

    return app


app = create_app()
