import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError

from app.models import Role, User
from tests.conftest import alembic_config


def test_seeded_roles_exist(db_session):
    codes = set(db_session.scalars(select(Role.code)))
    assert {"admin", "planner"} <= codes


def test_user_requires_valid_role_foreign_key(db_session):
    db_session.add(User(email="x@example.com", full_name="Test", role_id=9999))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_created_with_timestamps(db_session):
    role = db_session.scalar(select(Role).where(Role.code == "planner"))
    user = User(email="timestamps@example.com", full_name="Planner", role=role)
    db_session.add(user)
    db_session.flush()
    assert user.id is not None
    assert user.created_at is not None and user.updated_at is not None


def test_migrations_upgrade_and_downgrade_cleanly(tmp_path):
    url = f"sqlite:///{(tmp_path / 'roundtrip.db').as_posix()}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    assert {"roles", "users", "app_settings"} <= set(inspect(engine).get_table_names())
    command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
