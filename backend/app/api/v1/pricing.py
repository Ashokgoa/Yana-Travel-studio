"""Pricing & costing (Phase 7). Internal: planners and administrators see costs and margins."""

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DB, AdminUser, CurrentUser
from app.schemas.pricing import (
    LineOverride, ManualLineIn, PricingDefaults, PricingSettingsUpdate, PricingView, QuoteIn, StayRateOverride, SupplierRateIn, SupplierRateOut,
)
from app.services.pricing_service import PricingService
from app.services.supplier_rate_service import SupplierRateService

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


# ------------------------------------------------------------------ supplier quotes and rate cards (Phase 8c)
@router.put(f"{P}/quote", response_model=PricingView, summary="Record a supplier's price for a cost line (status, reference, currency)")
def quote(itinerary_id: int, body: QuoteIn, db: DB, user: CurrentUser, version: int | None = None):
    return PricingService(db, user).quote(itinerary_id, body, version)


@router.delete(f"{P}/quote", response_model=PricingView, summary="Remove a supplier quote from a cost line")
def clear_quote(itinerary_id: int, db: DB, user: CurrentUser, key: str = Query(min_length=1, max_length=200), version: int | None = None):
    return PricingService(db, user).clear_quote(itinerary_id, key, version)


@router.get("/supplier-rates", response_model=list[SupplierRateOut], summary="Active supplier rates (optionally by category, valid on a date)")
def search_rates(db: DB, _: CurrentUser, category: str | None = None, on: date | None = None, supplier_id: int | None = None):
    return SupplierRateService(db).search(category, on, supplier_id)


@router.get("/suppliers/{supplier_id}/rates", response_model=list[SupplierRateOut], summary="A supplier's rate card")
def supplier_rates(supplier_id: int, db: DB, _: CurrentUser):
    return SupplierRateService(db).for_supplier(supplier_id)


@router.post("/suppliers/{supplier_id}/rates", response_model=SupplierRateOut, status_code=201, summary="Add a rate to a supplier's rate card")
def add_rate(supplier_id: int, body: SupplierRateIn, db: DB, _: CurrentUser):
    return SupplierRateService(db).create(supplier_id, body)


@router.put("/supplier-rates/{rate_id}", response_model=SupplierRateOut, summary="Edit a supplier rate")
def edit_rate(rate_id: int, body: SupplierRateIn, db: DB, _: CurrentUser):
    return SupplierRateService(db).update(rate_id, body)


@router.delete("/supplier-rates/{rate_id}", status_code=204, summary="Delete a supplier rate")
def delete_rate(rate_id: int, db: DB, _: CurrentUser):
    SupplierRateService(db).delete(rate_id)
