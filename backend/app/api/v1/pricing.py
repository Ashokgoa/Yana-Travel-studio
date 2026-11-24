"""Pricing & costing (Phase 7). Internal: planners and administrators see costs and margins."""

from fastapi import APIRouter, Query

from app.api.deps import DB, AdminUser, CurrentUser
from app.schemas.pricing import LineOverride, ManualLineIn, PricingDefaults, PricingSettingsUpdate, PricingView, StayRateOverride
from app.services.pricing_service import PricingService

router = APIRouter(tags=["Pricing"])
P = "/itineraries/{itinerary_id}/pricing"


@router.get(P, response_model=PricingView, summary="Pricing sheet of a version (created from the defaults on first use)")
def view(itinerary_id: int, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).view(itinerary_id, version)


@router.patch(P, response_model=PricingView, summary="Margins, discount, adjustment, rounding, travellers, currency")
def update(itinerary_id: int, body: PricingSettingsUpdate, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).update(itinerary_id, body, version)


@router.put(f"{P}/overrides", response_model=PricingView, summary="Override an automatic cost line (cost, quantity, include)")
def override(itinerary_id: int, body: LineOverride, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).override(itinerary_id, body, version)


@router.delete(f"{P}/overrides", response_model=PricingView, summary="Back to the automatic values for a line")
def reset_override(itinerary_id: int, db: DB, user: CurrentUser, key: str = Query(min_length=1, max_length=200), version: int | None = None):
    return PricingService(db, user).reset_override(itinerary_id, key, version)


@router.put(f"{P}/stay-rates", response_model=PricingView, summary="Override the double/single room rate of a stay (both empty = reset)")
def stay_rate(itinerary_id: int, body: StayRateOverride, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).stay_rate(itinerary_id, body, version)


@router.post(f"{P}/lines", response_model=PricingView, status_code=201, summary="Add an extra cost line (guide, tolls, extras)")
def add_line(itinerary_id: int, body: ManualLineIn, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).add_line(itinerary_id, body, version)


@router.put(f"{P}/lines/{{line_id}}", response_model=PricingView, summary="Edit an extra cost line")
def update_line(itinerary_id: int, line_id: int, body: ManualLineIn, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).update_line(itinerary_id, line_id, body, version)


@router.delete(f"{P}/lines/{{line_id}}", response_model=PricingView, summary="Remove an extra cost line")
def delete_line(itinerary_id: int, line_id: int, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).delete_line(itinerary_id, line_id, version)


@router.get("/settings/pricing", response_model=PricingDefaults, summary="Pricing defaults")
def get_defaults(db: DB, _: CurrentUser):
    return PricingService(db).defaults()


@router.put("/settings/pricing", response_model=PricingDefaults, summary="Update pricing defaults (administrators)")
def save_defaults(body: PricingDefaults, db: DB, _: AdminUser):
    return PricingService(db).save_defaults(body)
