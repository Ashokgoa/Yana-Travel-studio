"""Backups and restore (Phase 8b).

A backup is one zip in `database/backups/`: a consistent copy of the SQLite
database (made with SQLite's online backup API, safe while the app runs), the
uploaded images, the generated PDFs and a manifest. Restore replaces all three
and is run from the command line while the app is stopped
(`scripts\\restore.ps1`), after taking a safety backup of the current state.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import DomainError

NAME_RE = re.compile(r"^yana_backup_[A-Za-z0-9_-]{1,80}\.zip$")
DB_ENTRY = "database/yana_studio.db"


def _db_path(settings: Settings) -> Path:
    if not settings.is_sqlite:
        raise DomainError("Backups from the app support SQLite only; use your database server's backup tools.", status.HTTP_400_BAD_REQUEST, "not_sqlite")
    return Path(settings.database_url.split("sqlite:///", 1)[1])


def _ensure_not_in_use(db_path: Path) -> None:
    """Refuse to restore while the app has the database open (Windows refuses to rename an open file)."""
    probe = db_path.with_name(db_path.name + ".restore-check")
    try:
        db_path.rename(probe)
    except PermissionError as exc:
        raise DomainError("The database is in use. Stop YANA Travel Studio first, then restore.", 409, "database_in_use") from exc
    probe.rename(db_path)


def _add_tree(z: zipfile.ZipFile, root: Path, prefix: str) -> int:
    count = 0
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if p.is_file():
                z.write(p, f"{prefix}/{p.relative_to(root).as_posix()}")
                count += 1
    return count


class BackupService:
    def __init__(self, db: Session | None = None, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.dir = self.settings.backups_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ create / list / read / delete
    def create(self, created_by: str | None = None, label: str | None = None) -> dict:
        src_path = _db_path(self.settings)
        stamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")
        name = f"yana_backup_{stamp}{'_' + label if label else ''}.zip"
        target = self.dir / name
        n = 1
        while target.exists():  # two backups in the same second
            target = self.dir / name.replace(".zip", f"-{n}.zip")
            n += 1
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "yana_studio.db"
            src = sqlite3.connect(src_path)
            dst = sqlite3.connect(copy)
            try:
                src.backup(dst)  # consistent snapshot even while the app is writing
                revision = dst.execute("SELECT version_num FROM alembic_version").fetchone()
                counts = {t: dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608 (fixed table names)
                          for t in ("enquiries", "itineraries", "hotels", "attractions", "media", "proposal_exports")}
            finally:
                src.close()
                dst.close()
            partial = target.with_suffix(".partial")
            with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(copy, DB_ENTRY)
                files = _add_tree(z, self.settings.uploads_dir, "uploads") + _add_tree(z, self.settings.exports_dir, "exports")
                manifest = {"app": self.settings.app_name, "app_version": self.settings.app_version,
                            "created_at": datetime.now(UTC).isoformat(), "created_by": created_by,
                            "alembic_revision": revision[0] if revision else None, "counts": counts, "files": files}
                z.writestr("manifest.json", json.dumps(manifest, indent=2))
            partial.replace(target)
        return self.info(target.name)

    def _path(self, name: str) -> Path:
        if not NAME_RE.match(name):  # plain file names only: no folders, no ".."
            raise DomainError("Backup not found.", status.HTTP_404_NOT_FOUND, "not_found")
        path = (self.dir / name).resolve()
        if path.parent != self.dir.resolve() or not path.is_file():
            raise DomainError("Backup not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return path

    def info(self, name: str) -> dict:
        path = self._path(name)
        try:
            with zipfile.ZipFile(path) as z:
                manifest = json.loads(z.read("manifest.json"))
        except (KeyError, zipfile.BadZipFile, json.JSONDecodeError):
            manifest = {}
        return {"name": path.name, "size_bytes": path.stat().st_size,
                "created_at": manifest.get("created_at") or datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
                "created_by": manifest.get("created_by"), "counts": manifest.get("counts", {}), "files": manifest.get("files"),
                "alembic_revision": manifest.get("alembic_revision"), "valid": bool(manifest)}

    def list(self) -> list[dict]:
        items = [self.info(p.name) for p in self.dir.glob("yana_backup_*.zip")]
        return sorted(items, key=lambda x: x["created_at"], reverse=True)

    def file(self, name: str) -> Path:
        return self._path(name)

    def delete(self, name: str) -> None:
        self._path(name).unlink()

    # ------------------------------------------------------------------ restore (command line, app stopped)
    def restore(self, zip_path: Path, created_by: str = "restore") -> dict:
        zip_path = Path(zip_path)
        if not zip_path.is_file():
            raise DomainError(f"File not found: {zip_path}", 404, "not_found")
        db_path = _db_path(self.settings)
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            with zipfile.ZipFile(zip_path) as z:
                names = z.namelist()
                if "manifest.json" not in names or DB_ENTRY not in names:
                    raise DomainError("This is not a YANA backup (manifest or database missing).", 400, "invalid_backup")
                for n in names:  # refuse path traversal
                    if n.startswith(("/", "\\")) or ".." in Path(n).parts:
                        raise DomainError("The backup contains an unsafe file path.", 400, "invalid_backup")
                z.extractall(tmpdir)
            restored_db = tmpdir / DB_ENTRY
            check = sqlite3.connect(restored_db)
            try:
                ok = check.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                check.close()
            if ok != "ok":
                raise DomainError("The database in this backup is damaged.", 400, "invalid_backup")

            if db_path.exists():
                _ensure_not_in_use(db_path)
            safety = self.create(created_by=created_by, label="before-restore") if db_path.exists() else None
            try:
                for side in (db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")):
                    side.unlink(missing_ok=True)  # a stale journal must never be applied to the restored file
                shutil.copyfile(restored_db, db_path)
            except PermissionError as exc:
                raise DomainError("The database is in use. Stop YANA Travel Studio first, then restore.", 409, "database_in_use") from exc
            for folder, target in (("uploads", self.settings.uploads_dir), ("exports", self.settings.exports_dir)):
                if target.exists():
                    shutil.rmtree(target)
                if (tmpdir / folder).is_dir():
                    shutil.copytree(tmpdir / folder, target)
                else:
                    target.mkdir(parents=True, exist_ok=True)
            manifest = json.loads((tmpdir / "manifest.json").read_text(encoding="utf-8"))
        return {"restored": zip_path.name, "safety_backup": safety["name"] if safety else None, "manifest": manifest}

