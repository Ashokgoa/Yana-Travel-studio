"""Test configuration.

Every test session uses a throwaway SQLite database and storage folders in a
temporary directory, so the real local database is never touched.
"""

import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="yana_test_"))
os.environ["YANA_ENVIRONMENT"] = "test"
os.environ["YANA_DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["YANA_UPLOADS_DIR"] = str(_TMP / "uploads")
os.environ["YANA_EXPORTS_DIR"] = str(_TMP / "exports")
os.environ["YANA_BACKUPS_DIR"] = str(_TMP / "backups")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    command.upgrade(alembic_config(os.environ["YANA_DATABASE_URL"]), "head")
    yield


@pytest.fixture(scope="session")
def tmp_root() -> Path:
    return _TMP


@pytest.fixture()
def client():
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    from app.database.session import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
