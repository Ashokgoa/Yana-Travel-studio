"""Application configuration.

All environment-specific values come from environment variables or a `.env`
file (see `.env.example` at the project root). Nothing in application logic
should hardcode an absolute path, URL or secret.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> project root is three parents above `app`.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        env_prefix="YANA_",
        extra="ignore",
    )

    app_name: str = "YANA Travel Studio"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|test|production)$")
    debug: bool = False

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database. SQLite for local use; any SQLAlchemy URL (e.g. PostgreSQL) works later.
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'database' / 'yana_studio.db').as_posix()}"

    # Storage locations (relative paths are resolved against the project root).
    uploads_dir: Path = Path("uploads")
    exports_dir: Path = Path("exports")
    backups_dir: Path = Path("database") / "backups"

    # Upload limits (used from Phase 2 onwards).
    max_upload_mb: int = Field(default=10, ge=1, le=100)
    allowed_image_extensions: list[str] = [".jpg", ".jpeg", ".png", ".webp"]

    @field_validator("uploads_dir", "exports_dir", "backups_dir")
    @classmethod
    def _resolve_against_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else (PROJECT_ROOT / value).resolve()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
