from pathlib import Path

from app.core.config import PROJECT_ROOT, Settings


def test_relative_storage_paths_resolve_to_project_root():
    s = Settings(uploads_dir=Path("uploads"), _env_file=None)
    assert s.uploads_dir == (PROJECT_ROOT / "uploads").resolve()


def test_default_database_is_sqlite_in_project_database_folder(monkeypatch):
    monkeypatch.delenv("YANA_DATABASE_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.is_sqlite
    assert s.database_url.endswith("database/yana_studio.db")
