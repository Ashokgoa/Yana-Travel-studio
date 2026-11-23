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


_RESERVED_ISO = {"PT", "MT", "QX"}  # used literally by some tests
_ISO_CODES = iter(a + b for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for b in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if a + b not in _RESERVED_ISO)


def unique_iso() -> str:
    """A two-letter country code never used before in this test session (no random collisions)."""
    return next(_ISO_CODES)


ADMIN = {"email": "admin@example.com", "password": "admin-pass-123", "full_name": "Test Admin"}
PLANNER = {"email": "planner@example.com", "password": "planner-pass-123", "full_name": "Test Planner"}


@pytest.fixture(scope="session", autouse=True)
def seeded_users(migrated_database):
    from app.database.session import SessionLocal
    from app.models.enums import RoleCode
    from app.schemas.user import UserCreate
    from app.services.user_service import UserService

    with SessionLocal() as db:
        service = UserService(db)
        service.create(UserCreate(role=RoleCode.ADMIN, **ADMIN))
        service.create(UserCreate(role=RoleCode.PLANNER, **PLANNER))


def _logged_in_client(credentials: dict):
    from app.main import create_app

    test_client = TestClient(create_app())
    test_client.__enter__()
    response = test_client.post(
        "/api/v1/auth/login", json={"email": credentials["email"], "password": credentials["password"]}
    )
    assert response.status_code == 200, response.text
    return test_client


@pytest.fixture()
def admin_client():
    c = _logged_in_client(ADMIN)
    yield c
    c.__exit__(None, None, None)


@pytest.fixture()
def planner_client():
    c = _logged_in_client(PLANNER)
    yield c
    c.__exit__(None, None, None)


@pytest.fixture()
def db_session():
    from app.database.session import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
