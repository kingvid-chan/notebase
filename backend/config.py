"""应用配置，从环境变量 / .env 文件读取。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-to-random-string"
    DATABASE_URL: str = "sqlite+aiosqlite:///./notebase.db"
    BASE_PATH: str = "/projects/notebase"
    VERSION: str = "0.0.1"
    LOG_LEVEL: str = "INFO"
    SESSION_MAX_AGE: int = 86400  # 24 小时

    # 演示账号
    DEMO_USER1: str = "alice"
    DEMO_PASS1: str = "demo123"
    DEMO_USER2: str = "bob"
    DEMO_PASS2: str = "demo123"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
