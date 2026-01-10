import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "CCG-Gateway"
    VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ccg_gateway.db"

    # Gateway defaults
    GATEWAY_PORT: int = 7788
    GATEWAY_HOST: str = "127.0.0.1"

    # Timeout defaults (seconds)
    STREAM_FIRST_BYTE_TIMEOUT: int = 30
    STREAM_IDLE_TIMEOUT: int = 60
    NON_STREAM_TIMEOUT: int = 120

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure data directory exists
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
