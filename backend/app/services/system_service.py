"""System health and environment information."""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.system import ComponentStatus, HealthResponse


def check_health(db: Session, settings: Settings) -> HealthResponse:
    database = _check_database(db)
    storage = _check_directory(settings.uploads_dir)
    exports = _check_directory(settings.exports_dir)
    overall = "ok" if all(c.status == "ok" for c in (database, storage, exports)) else "degraded"
    return HealthResponse(
        status=overall,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=database,
        storage=storage,
        exports=exports,
    )


def _check_database(db: Session) -> ComponentStatus:
    try:
        db.execute(text("SELECT 1"))
        bind = db.get_bind()
        if not inspect(bind).has_table("alembic_version"):
            return ComponentStatus(status="error", detail="Database not migrated. Run: alembic upgrade head")
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        return ComponentStatus(status="ok", detail=f"{bind.dialect.name}, migration {revision}")
    except Exception as exc:  # report, never crash the health check
        return ComponentStatus(status="error", detail=f"Database unavailable: {exc.__class__.__name__}")


def _check_directory(path) -> ComponentStatus:
    if path.is_dir():
        return ComponentStatus(status="ok", detail="writable directory available")
    return ComponentStatus(status="error", detail="directory missing")
