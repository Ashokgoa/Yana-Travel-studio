from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.system import HealthResponse
from app.services.system_service import check_health

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Application health check")
def health(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> HealthResponse:
    return check_health(db, settings)
