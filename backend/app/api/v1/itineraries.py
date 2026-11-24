"""Itinerary generation and viewing (PRD Part 13). Planners and admins."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DB, CurrentUser, Pagination
from app.schemas.common import Page
from app.schemas.itinerary import GenerateRequest, ItineraryDetail, ItinerarySummary, Strategy
from app.services import itinerary_presenter as present
from app.services.itinerary_service import ItineraryService

router = APIRouter(tags=["Itineraries"])


@router.post("/enquiries/{enquiry_id}/itineraries/generate", response_model=list[ItinerarySummary],
             status_code=status.HTTP_201_CREATED,
             summary="Generate itinerary alternatives (Classic, Scenic, Premium) from the captured requirements")
def generate(enquiry_id: int, db: DB, user: CurrentUser, body: GenerateRequest | None = None):
    created = ItineraryService(db).generate(enquiry_id, user, (body or GenerateRequest()).strategies)
    return present.summaries(db, created)


@router.get("/enquiries/{enquiry_id}/itineraries", response_model=list[ItinerarySummary],
            summary="Itineraries of an enquiry (latest generation first)")
def for_enquiry(enquiry_id: int, db: DB, _: CurrentUser):
    return present.summaries(db, ItineraryService(db).list_for_enquiry(enquiry_id))


@router.get("/itineraries", response_model=Page[ItinerarySummary], summary="All saved itineraries")
def list_itineraries(db: DB, _: CurrentUser, page: Pagination, q: str | None = None,
                     strategy: Annotated[Strategy | None, Query()] = None):
    items, total = ItineraryService(db).list_all(q, strategy, page.offset, page.page_size)
    return Page(items=present.summaries(db, items), total=total, page=page.page, page_size=page.page_size)


@router.get("/itineraries/{itinerary_id}", response_model=ItineraryDetail, summary="Full day-by-day itinerary")
def get_itinerary(itinerary_id: int, db: DB, _: CurrentUser):
    return present.detail(db, ItineraryService(db).get(itinerary_id))
