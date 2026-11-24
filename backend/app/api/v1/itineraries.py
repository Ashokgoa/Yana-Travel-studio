"""Itinerary generation and viewing (PRD Part 13). Planners and admins."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, status

from app.api.deps import DB, CurrentUser, Pagination
from app.schemas.common import Page
from app.schemas.itinerary import (
    ActivityCreate, ActivityMove, ActivityUpdate, DayUpdate, GenerateRequest, HotelReplace, ItineraryDetail,
    ItinerarySummary, LegModeUpdate, MealUpdate, SaveVersionRequest, Strategy, VehicleUpdate, VersionDiff, VersionInfo,
)
from app.services import itinerary_presenter as present
from app.services import itinerary_versions
from app.services.itinerary_editor import ItineraryEditor
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


@router.get("/itineraries/{itinerary_id}", response_model=ItineraryDetail,
            summary="Full day-by-day itinerary (latest version, or `?version=N`); warnings and costs are re-checked live")
def get_itinerary(itinerary_id: int, db: DB, _: CurrentUser, version: Annotated[int | None, Query(ge=1)] = None):
    return present.detail(db, ItineraryService(db).get(itinerary_id), version)


# ------------------------------------------------------------------ versions (PRD 14.5)
edit_tag = ["Itinerary builder"]


def _fresh(db, itinerary_id: int) -> ItineraryDetail:
    db.expire_all()
    return present.detail(db, ItineraryService(db).get(itinerary_id))


@router.get("/itineraries/{itinerary_id}/versions", response_model=list[VersionInfo], tags=edit_tag, summary="All versions, newest first")
def list_versions(itinerary_id: int, db: DB, _: CurrentUser):
    return itinerary_versions.versions(db, ItineraryService(db).get(itinerary_id))


@router.get("/itineraries/{itinerary_id}/versions/compare", response_model=VersionDiff, tags=edit_tag, summary="What changed between two versions")
def compare_versions(itinerary_id: int, db: DB, _: CurrentUser, a: Annotated[int, Query(ge=1)], b: Annotated[int, Query(ge=1)]):
    return itinerary_versions.compare(db, ItineraryService(db).get(itinerary_id), a, b)


@router.post("/itineraries/{itinerary_id}/edit", response_model=ItineraryDetail, tags=edit_tag,
             summary="Start editing: creates a working copy if the latest version is saved/read-only")
def start_editing(itinerary_id: int, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).start_editing(itinerary_id)
    return _fresh(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/versions", response_model=ItineraryDetail, tags=edit_tag,
             summary="Save the working copy as a named, read-only version")
def save_version(itinerary_id: int, body: SaveVersionRequest, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).save_version(itinerary_id, body.label, body.notes)
    return _fresh(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/versions/{version_number}/restore", response_model=ItineraryDetail, tags=edit_tag,
             summary="Restore an earlier version as a new working copy (nothing is overwritten)")
def restore_version(itinerary_id: int, version_number: int, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).restore(itinerary_id, version_number)
    return _fresh(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/duplicate", response_model=ItinerarySummary, status_code=status.HTTP_201_CREATED,
             tags=edit_tag, summary="Duplicate the itinerary (latest version) as a new itinerary")
def duplicate(itinerary_id: int, db: DB, user: CurrentUser):
    new = ItineraryEditor(db, user).duplicate(itinerary_id)
    return present.summaries(db, [ItineraryService(db).get(new.id)])[0]


# ------------------------------------------------------------------ edits (working copy only; 409 version_locked otherwise)
@router.post("/itineraries/{itinerary_id}/days/{day_number}/add-after", response_model=ItineraryDetail, tags=edit_tag, summary="Add a day after this day")
def add_day(itinerary_id: int, day_number: int, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).add_day_after(itinerary_id, day_number)
    return _fresh(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/days/{day_number}/duplicate", response_model=ItineraryDetail, tags=edit_tag, summary="Duplicate a day")
def duplicate_day(itinerary_id: int, day_number: int, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).add_day_after(itinerary_id, day_number, duplicate=True)
    return _fresh(db, itinerary_id)


@router.delete("/itineraries/{itinerary_id}/days/{day_number}", response_model=ItineraryDetail, tags=edit_tag, summary="Remove a day")
def remove_day(itinerary_id: int, day_number: int, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).remove_day(itinerary_id, day_number)
    return _fresh(db, itinerary_id)


@router.patch("/itineraries/{itinerary_id}/days/{day_number}", response_model=ItineraryDetail, tags=edit_tag, summary="Edit a day's title/description")
def update_day(itinerary_id: int, day_number: int, body: DayUpdate, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).update_day(itinerary_id, day_number, body.title, body.description)
    return _fresh(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/days/{day_number}/activities", response_model=ItineraryDetail, tags=edit_tag,
             summary="Add sightseeing (attraction_id) or a free-time/custom activity")
def add_activity(itinerary_id: int, day_number: int, body: ActivityCreate, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).add_activity(itinerary_id, day_number, **body.model_dump())
    return _fresh(db, itinerary_id)


@router.patch("/itineraries/{itinerary_id}/activities/{activity_id}", response_model=ItineraryDetail, tags=edit_tag, summary="Edit an activity")
def update_activity(itinerary_id: int, activity_id: int, body: ActivityUpdate, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).update_activity(itinerary_id, activity_id, body.model_dump(exclude_unset=True))
    return _fresh(db, itinerary_id)


@router.post("/itineraries/{itinerary_id}/activities/{activity_id}/move", response_model=ItineraryDetail, tags=edit_tag,
             summary="Move an activity to a position (and optionally slot) on any day")
def move_activity(itinerary_id: int, activity_id: int, body: ActivityMove, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).move_activity(itinerary_id, activity_id, body.day_number, body.position, body.time_slot)
    return _fresh(db, itinerary_id)


@router.delete("/itineraries/{itinerary_id}/activities/{activity_id}", response_model=ItineraryDetail, tags=edit_tag, summary="Remove an activity")
def remove_activity(itinerary_id: int, activity_id: int, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).remove_activity(itinerary_id, activity_id)
    return _fresh(db, itinerary_id)


@router.put("/itineraries/{itinerary_id}/days/{day_number}/meals/{meal}", response_model=ItineraryDetail, tags=edit_tag,
            summary="Set a meal: at the hotel, a restaurant from inventory, own arrangement, or none")
def set_meal(itinerary_id: int, day_number: int, meal: Literal["breakfast", "lunch", "dinner"], body: MealUpdate, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).set_meal(itinerary_id, day_number, meal, body.arrangement, body.restaurant_id, body.note)
    return _fresh(db, itinerary_id)


@router.put("/itineraries/{itinerary_id}/stays/{stay_id}/hotel", response_model=ItineraryDetail, tags=edit_tag,
            summary="Replace the hotel of a stay (same city; rooms are re-mapped and re-priced)")
def replace_hotel(itinerary_id: int, stay_id: int, body: HotelReplace, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).replace_hotel(itinerary_id, stay_id, body.hotel_id)
    return _fresh(db, itinerary_id)


@router.put("/itineraries/{itinerary_id}/vehicle", response_model=ItineraryDetail, tags=edit_tag, summary="Change the vehicle for the trip")
def set_vehicle(itinerary_id: int, body: VehicleUpdate, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).set_vehicle(itinerary_id, body.vehicle_id)
    return _fresh(db, itinerary_id)


@router.patch("/itineraries/{itinerary_id}/transports/{transport_id}", response_model=ItineraryDetail, tags=edit_tag,
              summary="Change a leg's transport mode (e.g. train)")
def set_leg_mode(itinerary_id: int, transport_id: int, body: LegModeUpdate, db: DB, user: CurrentUser):
    ItineraryEditor(db, user).set_leg_mode(itinerary_id, transport_id, body.mode)
    return _fresh(db, itinerary_id)
