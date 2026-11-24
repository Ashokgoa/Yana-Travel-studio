"""Visual itinerary builder (PRD Part 14): edits, versions, restore, duplicate.

Versioning model
- Saved versions (incl. v1 "Generated") are read-only snapshots (`is_locked`).
- Editing always happens on a *working copy*: the latest version when it is
  unlocked. `start_editing` clones the latest locked version into a new one.
- `save_version` locks the working copy with a label; the next edit needs a new copy.

Consistency
- Day numbers/dates are always contiguous from the version start date.
- After any change to the day structure, stays (hotel per consecutive nights in
  a city) and inter-city legs are REBUILT from the days, keeping existing hotel
  choices and transport where they still apply. Totals are recomputed.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.engines.geo import drive_minutes, road_km
from app.models import (
    Attraction, City, Hotel, Itinerary, ItineraryActivity, ItineraryDay, ItineraryMeal, ItineraryStay,
    ItineraryTransport, ItineraryVersion, Restaurant, User, Vehicle,
)
from app.services.itinerary_service import ItineraryService

SLOTS = ("morning", "afternoon", "full_day", "evening")
CUSTOM_TYPES = ("free_time", "custom", "transfer")
MEALS = ("breakfast", "lunch", "dinner")


def _error(message: str, code: str, http: int = status.HTTP_400_BAD_REQUEST) -> DomainError:
    return DomainError(message, http, code)


class ItineraryEditor:
    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user
        self.service = ItineraryService(db)

    # ================================================================= versions
    def _latest(self, itinerary_id: int) -> tuple[Itinerary, ItineraryVersion]:
        it = self.service.get(itinerary_id)
        return it, self.service.current_version(it)

    def working(self, itinerary_id: int) -> ItineraryVersion:
        """The editable working copy; 409 if the latest version is a saved (locked) snapshot."""
        _, v = self._latest(itinerary_id)
        if v.is_locked:
            raise _error(f"Version {v.version_number} ({v.label}) is saved and read-only. Start editing to create a working copy.",
                         "version_locked", status.HTTP_409_CONFLICT)
        return v

    def start_editing(self, itinerary_id: int) -> ItineraryVersion:
        it, v = self._latest(itinerary_id)
        if not v.is_locked:
            return v
        copy = self._clone(v, it, label="Working draft", notes=f"Based on version {v.version_number} ({v.label})")
        self.db.commit()
        return copy

    def save_version(self, itinerary_id: int, label: str, notes: str | None) -> ItineraryVersion:
        v = self.working(itinerary_id)
        v.label, v.notes, v.is_locked = label, notes or v.notes, True
        self.db.commit()
        return v

    def restore(self, itinerary_id: int, version_number: int) -> ItineraryVersion:
        it, latest = self._latest(itinerary_id)
        source = next((x for x in it.versions if x.version_number == version_number), None)
        if source is None:
            raise _error("Version not found.", "not_found", status.HTTP_404_NOT_FOUND)
        source = self.db.get(ItineraryVersion, source.id)
        if not latest.is_locked:  # discard nothing silently: keep the unsaved draft as a saved version first
            latest.is_locked = True
            latest.label = f"{latest.label} (auto-saved before restore)"
        copy = self._clone(source, it, label=f"Restored from v{version_number}", notes=f"Copy of version {version_number} ({source.label})")
        self.db.commit()
        return copy

    def duplicate(self, itinerary_id: int) -> Itinerary:
        it, v = self._latest(itinerary_id)
        new = Itinerary(enquiry_id=it.enquiry_id, kind=it.kind, title=f"{it.title} (copy)"[:200], strategy=it.strategy,
                        batch=it.batch, created_by_id=self.user.id)
        self.db.add(new)
        self.db.flush()
        self._clone(v, new, label="Duplicated", notes=f"Duplicated from itinerary #{it.id} version {v.version_number}", number=1)
        self.db.commit()
        return new

    def _clone(self, src: ItineraryVersion, it: Itinerary, label: str, notes: str | None, number: int | None = None) -> ItineraryVersion:
        if number is None:
            number = (self.db.scalar(select(func.max(ItineraryVersion.version_number)).where(ItineraryVersion.itinerary_id == it.id)) or 0) + 1
        report = deepcopy(src.generation_report or {})
        v = ItineraryVersion(itinerary_id=it.id, version_number=number, label=label, notes=notes, start_date=src.start_date,
                             total_days=src.total_days, total_nights=src.total_nights, vehicle_id=src.vehicle_id,
                             generation_report=report, is_locked=False, created_by_id=self.user.id)
        for d in src.days:
            day = ItineraryDay(day_number=d.day_number, date=d.date, city_id=d.city_id, overnight_city_id=d.overnight_city_id,
                               title=d.title, description=d.description)
            day.activities = [ItineraryActivity(sort_order=a.sort_order, time_slot=a.time_slot, activity_type=a.activity_type,
                                                attraction_id=a.attraction_id, title=a.title, description=a.description,
                                                duration_min=a.duration_min) for a in d.activities]
            day.meals = [ItineraryMeal(sort_order=m.sort_order, meal=m.meal, arrangement=m.arrangement,
                                       restaurant_id=m.restaurant_id, note=m.note) for m in d.meals]
            v.days.append(day)
        v.stays = [ItineraryStay(city_id=s.city_id, hotel_id=s.hotel_id, check_in_day=s.check_in_day, nights=s.nights,
                                 rooms=deepcopy(s.rooms), alternative_hotel_ids=list(s.alternative_hotel_ids),
                                 estimated_cost=s.estimated_cost, note=s.note) for s in src.stays]
        v.transports = [ItineraryTransport(day_number=t.day_number, sort_order=t.sort_order, kind=t.kind, mode=t.mode,
                                           from_city_id=t.from_city_id, to_city_id=t.to_city_id, vehicle_id=t.vehicle_id,
                                           distance_km=t.distance_km, duration_min=t.duration_min, is_estimate=t.is_estimate,
                                           note=t.note) for t in src.transports]
        self.db.add(v)
        self.db.flush()
        # Pricing decisions (margins, overrides, extra lines) follow the content to the new version.
        from app.services.pricing_service import PricingService  # local import: pricing builds on the itinerary service
        PricingService(self.db, self.user).copy_sheet(src, v)
        return v

    # ================================================================= days
    def _day(self, v: ItineraryVersion, day_number: int) -> ItineraryDay:
        day = next((d for d in v.days if d.day_number == day_number), None)
        if day is None:
            raise _error(f"Day {day_number} not found.", "not_found", status.HTTP_404_NOT_FOUND)
        return day

    def add_day_after(self, itinerary_id: int, day_number: int, duplicate: bool = False) -> None:
        v = self.working(itinerary_id)
        days = sorted(v.days, key=lambda d: d.day_number)
        src = self._day(v, day_number)
        if src.overnight_city_id is None:
            raise _error("Days can't be added after the departure day. Add it before departure instead.", "invalid_position")
        new = ItineraryDay(day_number=0, date=src.date, city_id=src.overnight_city_id, overnight_city_id=src.overnight_city_id,
                           title=src.title if duplicate else f"{self._city_name(src.overnight_city_id)}: extra day")
        if duplicate:
            new.activities = [ItineraryActivity(sort_order=a.sort_order, time_slot=a.time_slot, activity_type=a.activity_type,
                                                attraction_id=a.attraction_id, title=a.title, description=a.description,
                                                duration_min=a.duration_min) for a in src.activities
                              if a.activity_type not in ("check_in", "check_out", "transfer", "arrival", "departure")]
            new.meals = [ItineraryMeal(sort_order=m.sort_order, meal=m.meal, arrangement=m.arrangement, restaurant_id=m.restaurant_id,
                                       note=m.note) for m in src.meals]
        else:
            new.activities = [ItineraryActivity(sort_order=0, time_slot="full_day", activity_type="free_time", title="Free day",
                                                description="At leisure, or add sightseeing.")]
            # Same city, so the same meal arrangements as the day it follows (breakfast is always at the hotel).
            new.meals = [ItineraryMeal(sort_order=MEALS.index(m.meal), meal=m.meal, arrangement=m.arrangement,
                                       restaurant_id=m.restaurant_id, note=m.note) for m in src.meals]
            if "breakfast" not in {m.meal for m in new.meals} and any(m.meal == "breakfast" for d in days for m in d.meals):
                new.meals.insert(0, ItineraryMeal(sort_order=0, meal="breakfast", arrangement="hotel"))
        index = days.index(src) + 1
        days.insert(index, new)
        v.days.append(new)
        self._renumber(v, days)
        self._rebuild(v)

    def remove_day(self, itinerary_id: int, day_number: int) -> None:
        v = self.working(itinerary_id)
        days = sorted(v.days, key=lambda d: d.day_number)
        day = self._day(v, day_number)
        if day is days[0] or day is days[-1]:
            raise _error("The arrival and departure days can't be removed.", "invalid_position")
        if len(days) <= 2:
            raise _error("An itinerary needs at least one night.", "invalid_position")
        days.remove(day)
        v.days.remove(day)
        self._renumber(v, days)
        self._rebuild(v)

    def update_day(self, itinerary_id: int, day_number: int, title: str | None, description: str | None) -> None:
        day = self._day(self.working(itinerary_id), day_number)
        if title is not None:
            day.title = title
        day.description = description
        self.db.commit()

    def _renumber(self, v: ItineraryVersion, ordered: list[ItineraryDay]) -> None:
        # Two passes avoid temporary clashes with the (version_id, day_number) unique constraint.
        for i, d in enumerate(ordered, start=1):
            d.day_number = 10_000 + i
        self.db.flush()
        for i, d in enumerate(ordered, start=1):
            d.day_number = i
            d.date = v.start_date + timedelta(days=i - 1)
        v.total_days = len(ordered)
        v.total_nights = len(ordered) - 1

    # ================================================================= activities
    def _activity(self, v: ItineraryVersion, activity_id: int) -> tuple[ItineraryDay, ItineraryActivity]:
        for d in v.days:
            for a in d.activities:
                if a.id == activity_id:
                    return d, a
        raise _error("Activity not found in the working version.", "not_found", status.HTTP_404_NOT_FOUND)

    def add_activity(self, itinerary_id: int, day_number: int, *, time_slot: str, attraction_id: int | None,
                     activity_type: str, title: str | None, description: str | None, duration_min: int | None) -> None:
        v = self.working(itinerary_id)
        day = self._day(v, day_number)
        if attraction_id:
            a = self.db.get(Attraction, attraction_id)
            if a is None or not a.is_active:
                raise _error("Selected sightseeing is not an active inventory record.", "invalid_reference")
            act = ItineraryActivity(time_slot=time_slot, activity_type="sightseeing", attraction_id=a.id, title=title or a.name,
                                    description=description, duration_min=duration_min or a.recommended_duration_min)
        else:
            if not title:
                raise _error("A title is required for a custom activity.", "invalid_activity")
            act = ItineraryActivity(time_slot=time_slot, activity_type=activity_type, title=title, description=description,
                                    duration_min=duration_min)
        act.sort_order = max((x.sort_order for x in day.activities), default=-1) + 1
        day.activities.append(act)
        self.db.commit()

    def update_activity(self, itinerary_id: int, activity_id: int, fields: dict) -> None:
        _, a = self._activity(self.working(itinerary_id), activity_id)
        for k in ("title", "description", "time_slot", "duration_min"):
            if k in fields:
                setattr(a, k, fields[k])
        self.db.commit()

    def remove_activity(self, itinerary_id: int, activity_id: int) -> None:
        day, a = self._activity(self.working(itinerary_id), activity_id)
        day.activities.remove(a)
        self.db.commit()

    def move_activity(self, itinerary_id: int, activity_id: int, to_day: int, position: int, time_slot: str | None) -> None:
        v = self.working(itinerary_id)
        src_day, a = self._activity(v, activity_id)
        dest = self._day(v, to_day)
        ordered_src = sorted(src_day.activities, key=lambda x: x.sort_order)
        ordered_src.remove(a)
        if dest is src_day:
            target = ordered_src
        else:
            for i, x in enumerate(ordered_src):
                x.sort_order = i
            src_day.activities.remove(a)
            dest.activities.append(a)
            target = sorted((x for x in dest.activities if x is not a), key=lambda x: x.sort_order)
        position = max(0, min(position, len(target)))
        target.insert(position, a)
        for i, x in enumerate(target):
            x.sort_order = i
        if time_slot:
            a.time_slot = time_slot
        self.db.commit()

    # ================================================================= meals, hotels, transport
    def set_meal(self, itinerary_id: int, day_number: int, meal: str, arrangement: str, restaurant_id: int | None, note: str | None) -> None:
        day = self._day(self.working(itinerary_id), day_number)
        if arrangement == "restaurant":
            r = self.db.get(Restaurant, restaurant_id) if restaurant_id else None
            if r is None or not r.is_active:
                raise _error("Choose an active restaurant from inventory.", "invalid_reference")
        existing = next((m for m in day.meals if m.meal == meal), None)
        if arrangement == "none":
            if existing:
                day.meals.remove(existing)
        elif existing:
            existing.arrangement, existing.restaurant_id, existing.note = arrangement, restaurant_id if arrangement == "restaurant" else None, note
        else:
            day.meals.append(ItineraryMeal(sort_order=MEALS.index(meal), meal=meal, arrangement=arrangement,
                                           restaurant_id=restaurant_id if arrangement == "restaurant" else None, note=note))
        for m in day.meals:
            m.sort_order = MEALS.index(m.meal)
        self.db.commit()

    def replace_hotel(self, itinerary_id: int, stay_id: int, hotel_id: int) -> None:
        v = self.working(itinerary_id)
        stay = next((s for s in v.stays if s.id == stay_id), None)
        if stay is None:
            raise _error("Hotel stay not found in the working version.", "not_found", status.HTTP_404_NOT_FOUND)
        hotel = self.db.get(Hotel, hotel_id)
        if hotel is None or not hotel.is_active:
            raise _error("Choose an active hotel from inventory.", "invalid_reference")
        if hotel.city_id != stay.city_id:
            raise _error("The hotel must be in the same city as the stay.", "city_mismatch")
        if stay.hotel_id and stay.hotel_id != hotel_id and stay.hotel_id not in stay.alternative_hotel_ids:
            stay.alternative_hotel_ids = [stay.hotel_id, *stay.alternative_hotel_ids][:3]
        stay.alternative_hotel_ids = [h for h in stay.alternative_hotel_ids if h != hotel_id]
        stay.hotel_id = hotel_id
        stay.rooms = self._map_rooms(hotel, stay.rooms, v.start_date + timedelta(days=stay.check_in_day - 1))
        stay.estimated_cost = self._stay_cost(stay)
        stay.note = "Availability not verified"
        self.db.commit()

    def set_vehicle(self, itinerary_id: int, vehicle_id: int | None) -> None:
        v = self.working(itinerary_id)
        if vehicle_id is not None:
            vehicle = self.db.get(Vehicle, vehicle_id)
            if vehicle is None or not vehicle.is_active:
                raise _error("Choose an active vehicle from inventory.", "invalid_reference")
        v.vehicle_id = vehicle_id
        for t in v.transports:
            if t.mode != "train":
                t.vehicle_id = vehicle_id
        self.db.commit()

    def set_leg_mode(self, itinerary_id: int, transport_id: int, mode: str) -> None:
        v = self.working(itinerary_id)
        leg = next((t for t in v.transports if t.id == transport_id), None)
        if leg is None:
            raise _error("Transport leg not found in the working version.", "not_found", status.HTTP_404_NOT_FOUND)
        leg.mode = mode
        leg.vehicle_id = None if mode == "train" else v.vehicle_id
        leg.note = "Train fare not in inventory; to be quoted." if mode == "train" else None
        self.db.commit()

    # ================================================================= rebuild helpers
    def _city_name(self, city_id: int | None) -> str:
        c = self.db.get(City, city_id) if city_id else None
        return c.name if c else "City"

    def _rebuild(self, v: ItineraryVersion) -> None:
        """Re-derive stays and legs from the (renumbered) days, keeping prior choices where possible."""
        days = sorted(v.days, key=lambda d: d.day_number)
        old_stays = sorted(v.stays, key=lambda s: s.check_in_day)
        segments: list[tuple[int, int, int]] = []  # (city_id, check_in_day, nights)
        for d in days:
            if d.overnight_city_id is None:
                continue
            if segments and segments[-1][0] == d.overnight_city_id and segments[-1][1] + segments[-1][2] == d.day_number:
                c, start, n = segments[-1]
                segments[-1] = (c, start, n + 1)
            else:
                segments.append((d.overnight_city_id, d.day_number, 1))
        used: set[int] = set()
        new_stays = []
        for city_id, start, n in segments:
            match = next((s for s in old_stays if s.city_id == city_id and s.id not in used), None)
            if match:
                used.add(match.id)
                stay = ItineraryStay(city_id=city_id, hotel_id=match.hotel_id, check_in_day=start, nights=n, rooms=deepcopy(match.rooms),
                                     alternative_hotel_ids=list(match.alternative_hotel_ids), note=match.note)
            else:
                stay = ItineraryStay(city_id=city_id, hotel_id=None, check_in_day=start, nights=n, rooms=[], alternative_hotel_ids=[],
                                     note="No hotel selected yet")
            stay.estimated_cost = self._stay_cost(stay)
            new_stays.append(stay)
        for s in list(v.stays):
            v.stays.remove(s)
        v.stays.extend(new_stays)

        # legs: keep airport transfers (re-dated), rebuild inter-city legs from city changes
        old_legs = list(v.transports)
        mode = next((t.mode for t in old_legs if t.mode != "train"), "coach")
        arrival = next((t for t in old_legs if t.kind == "airport_transfer" and t.from_city_id is None), None)
        departure = next((t for t in old_legs if t.kind == "airport_transfer" and t.to_city_id is None), None)
        new_legs = []
        if arrival:
            new_legs.append(self._copy_leg(arrival, day_number=1, to_city_id=days[0].overnight_city_id or days[0].city_id))
        prev_city = days[0].overnight_city_id
        for d in days[1:]:
            here = d.overnight_city_id or d.city_id
            if here != prev_city and prev_city is not None and d.overnight_city_id is not None:
                existing = next((t for t in old_legs if t.kind == "intercity" and t.from_city_id == prev_city and t.to_city_id == here), None)
                if existing:
                    new_legs.append(self._copy_leg(existing, day_number=d.day_number))
                else:
                    new_legs.append(self._new_leg(v, d.day_number, prev_city, here, mode))
                d.city_id = here
            if d.overnight_city_id is not None:
                prev_city = d.overnight_city_id
        if departure:
            last = days[-1]
            last.city_id = prev_city or last.city_id
            new_legs.append(self._copy_leg(departure, day_number=last.day_number, from_city_id=prev_city))
        for t in list(v.transports):
            v.transports.remove(t)
        for i, leg in enumerate(new_legs):
            leg.sort_order = i
        v.transports.extend(new_legs)
        self.db.commit()

    @staticmethod
    def _copy_leg(t: ItineraryTransport, day_number: int, **override) -> ItineraryTransport:
        fields = dict(kind=t.kind, mode=t.mode, from_city_id=t.from_city_id, to_city_id=t.to_city_id, vehicle_id=t.vehicle_id,
                      distance_km=t.distance_km, duration_min=t.duration_min, is_estimate=t.is_estimate, note=t.note)
        fields.update(override)
        return ItineraryTransport(day_number=day_number, **fields)

    def _new_leg(self, v: ItineraryVersion, day_number: int, from_id: int, to_id: int, mode: str) -> ItineraryTransport:
        a, b = self.db.get(City, from_id), self.db.get(City, to_id)
        km = road_km((a.latitude, a.longitude), (b.latitude, b.longitude)) if None not in (a.latitude, a.longitude, b.latitude, b.longitude) else None
        return ItineraryTransport(day_number=day_number, kind="intercity", mode=mode, from_city_id=from_id, to_city_id=to_id,
                                  vehicle_id=v.vehicle_id, distance_km=km, duration_min=drive_minutes(km) if km else None, is_estimate=True)

    def _map_rooms(self, hotel: Hotel, rooms: list[dict], on) -> list[dict]:
        mapped = []
        for r in rooms or [{"label": "Double", "count": 1}]:
            key = (r.get("label") or "").lower().split()[0] if r.get("label") else "double"
            rt = next((x for x in hotel.room_types if key and key in x.name.lower()), None) or (hotel.room_types[0] if hotel.room_types else None)
            price = None
            if rt:
                rate = next((x for x in hotel.rates if x.room_type_id == rt.id and x.valid_from <= on <= x.valid_to), None)
                price = rate.price if rate else rt.base_price
            mapped.append({"room_type_id": rt.id if rt else None, "label": rt.name if rt else r.get("label", "Room"), "count": r.get("count", 1),
                           "price": None if price is None else str(Decimal(price).quantize(Decimal("0.01")))})
        return mapped

    @staticmethod
    def _stay_cost(stay: ItineraryStay) -> Decimal | None:
        if not stay.hotel_id or not stay.rooms or any(r.get("price") is None for r in stay.rooms):
            return None
        return sum((Decimal(r["price"]) * r["count"] for r in stay.rooms), Decimal(0)) * stay.nights
