"""AI assistant (Phase 8): read requirements from text, itinerary suggestions, status.

Offline by default. Suggestions are proposals only; planners apply them one by one.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DB, CurrentUser
from app.schemas.itinerary import ItineraryDetail
from app.services import ai_provider, itinerary_suggestions
from app.services import itinerary_presenter as present
from app.services.ai_service import AIService, ReadResult
from app.services.itinerary_service import ItineraryService
from app.services.itinerary_suggestions import Suggestion

router = APIRouter(tags=["AI assistant"])


class ReadTextIn(BaseModel):
    text: str = Field(min_length=10, max_length=20000)


class ApplyIn(BaseModel):
    key: str = Field(min_length=1, max_length=200)


@router.get("/ai/status", summary="Which AI provider is active and whether data leaves this computer")
def ai_status(_: CurrentUser):
    return ai_provider.status()


@router.post("/enquiries/{enquiry_id}/requirements/read-text", response_model=ReadResult,
             summary="Propose requirement values from pasted text (e.g. an agent's email). Nothing is saved.")
def read_text(enquiry_id: int, body: ReadTextIn, db: DB, _: CurrentUser):
    return AIService(db).read_requirements(enquiry_id, body.text)


@router.get("/itineraries/{itinerary_id}/suggestions", response_model=list[Suggestion], summary="Suggested improvements (inventory only)")
def list_suggestions(itinerary_id: int, db: DB, _: CurrentUser, version: int | None = None):
    return itinerary_suggestions.suggestions(db, itinerary_id, version)


@router.post("/itineraries/{itinerary_id}/suggestions/apply", response_model=ItineraryDetail,
             summary="Apply one suggestion to the working copy (started from the latest version if needed)")
def apply_suggestion(itinerary_id: int, body: ApplyIn, db: DB, user: CurrentUser):
    itinerary_suggestions.apply(db, user, itinerary_id, body.key)
    db.expire_all()
    return present.detail(db, ItineraryService(db).get(itinerary_id))
