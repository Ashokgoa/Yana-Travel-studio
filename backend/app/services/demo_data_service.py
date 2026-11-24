"""Remove demonstration data (Phase 8b).

Only inventory rows flagged `is_demo` are touched (fictional hotels with their
rooms and rates, restaurants, vehicles, suppliers, and any demo sightseeing).
A demo record still used by an itinerary is deactivated instead of deleted, so
no itinerary or saved version breaks. Images stay in the image library; only
their links to removed records are dropped. Real countries, cities and
sightseeing are never demo data.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Attraction, Hotel, ItineraryActivity, ItineraryMeal, ItineraryStay, ItineraryTransport, ItineraryVersion, MediaLink, PricingLine,
    Restaurant, Supplier, Vehicle,
)

ENTITY = {Hotel: "hotel", Restaurant: "restaurant", Vehicle: "vehicle", Attraction: "attraction"}
LABELS = {"hotels": Hotel, "restaurants": Restaurant, "vehicles": Vehicle, "sightseeing": Attraction, "suppliers": Supplier}


class DemoDataService:
    def __init__(self, db: Session):
        self.db = db

    def _used(self) -> dict[type, set[int]]:
        hotels = set(self.db.scalars(select(ItineraryStay.hotel_id).where(ItineraryStay.hotel_id.is_not(None))))
        for alts in self.db.scalars(select(ItineraryStay.alternative_hotel_ids)):
            hotels.update(alts or [])
        vehicles = set(self.db.scalars(select(ItineraryVersion.vehicle_id).where(ItineraryVersion.vehicle_id.is_not(None)))) \
            | set(self.db.scalars(select(ItineraryTransport.vehicle_id).where(ItineraryTransport.vehicle_id.is_not(None))))
        return {
            Hotel: hotels,
            Restaurant: set(self.db.scalars(select(ItineraryMeal.restaurant_id).where(ItineraryMeal.restaurant_id.is_not(None)))),
            Vehicle: vehicles,
            Attraction: set(self.db.scalars(select(ItineraryActivity.attraction_id).where(ItineraryActivity.attraction_id.is_not(None)))),
        }

    def summary(self) -> dict:
        used = self._used()
        out = {}
        for label, model in LABELS.items():
            ids = set(self.db.scalars(select(model.id).where(model.is_demo.is_(True), model.is_active.is_(True))))
            in_use = len(ids & used.get(model, set())) if model is not Supplier else None
            out[label] = {"demo": len(ids), "in_use": in_use}
        out["total"] = sum(v["demo"] for v in out.values())
        return out

    def remove(self) -> dict:
        used = self._used()
        result = {}
        for model in (Hotel, Restaurant, Vehicle, Attraction):
            deleted = deactivated = 0
            for row in list(self.db.scalars(select(model).where(model.is_demo.is_(True)))):
                if row.id in used[model]:
                    if row.is_active:
                        row.is_active = False
                        deactivated += 1
                else:
                    self.db.execute(delete(MediaLink).where(MediaLink.entity_type == ENTITY[model], MediaLink.entity_id == row.id))
                    self.db.delete(row)
                    deleted += 1
            result[model.__tablename__] = {"deleted": deleted, "deactivated": deactivated}
        self.db.flush()
        # Suppliers last: keep (deactivated) any still referenced by remaining records or pricing lines.
        deleted = deactivated = 0
        for s in list(self.db.scalars(select(Supplier).where(Supplier.is_demo.is_(True)))):
            refs = sum(self.db.scalar(select(func.count()).select_from(m).where(m.supplier_id == s.id)) or 0
                       for m in (Hotel, Restaurant, Vehicle, Attraction, PricingLine))
            if refs:
                if s.is_active:
                    s.is_active = False
                    deactivated += 1
            else:
                self.db.delete(s)
                deleted += 1
        result["suppliers"] = {"deleted": deleted, "deactivated": deactivated}
        self.db.commit()
        return result
