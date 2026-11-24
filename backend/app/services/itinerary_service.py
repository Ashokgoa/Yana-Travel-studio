"""Generate, store and read itineraries (PRD Part 13).

The engine (`app.engines.itinerary_engine`) is pure; this service loads the
captured requirements and ACTIVE inventory, runs one or more strategies and
stores each result as an itinerary with version 1.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import DomainError
from app.engines import itinerary_engine as eng
from app.models import (
    Attraction, City, Enquiry, Hotel, Itinerary, ItineraryActivity, ItineraryDay, ItineraryMeal, ItineraryStay,
    ItineraryTransport, ItineraryVersion, Restaurant, User, Vehicle,
)
from app.services.requirement_service import RequirementService

STRATEGY_ORDER = ["classic", "scenic", "premium"]


def _money(v: Decimal | None) -> str | None:
    return None if v is None else str(Decimal(v).quantize(Decimal("0.01")))


class ItineraryService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------- generation
    def generate(self, enquiry_id: int, user: User, strategies: list[str] | None = None) -> list[Itinerary]:
        enquiry = self.db.get(Enquiry, enquiry_id)
        if enquiry is None:
            raise DomainError("Enquiry not found.", status.HTTP_404_NOT_FOUND, "not_found")
        req_out = RequirementService(self.db).get(enquiry_id)
        if not req_out.exists:
            raise DomainError("Capture the customer requirements before generating itineraries.",
                              status.HTTP_422_UNPROCESSABLE_CONTENT, "requirements_missing")
        if req_out.missing:
            raise DomainError("Requirements are incomplete: " + "; ".join(req_out.missing) + ".",
                              status.HTTP_422_UNPROCESSABLE_CONTENT, "requirements_incomplete")

        req = self._engine_requirements(req_out)
        inv = self._engine_inventory()
        strategies = [s for s in STRATEGY_ORDER if s in (strategies or STRATEGY_ORDER)]
        plans = []
        for s in strategies:
            try:
                plans.append(eng.generate(req, inv, s))
            except eng.GenerationError as exc:
                # Same requirements fail for every strategy; explain once, store nothing.
                raise DomainError("The itinerary cannot be generated: " + " ".join(exc.issues),
                                  status.HTTP_422_UNPROCESSABLE_CONTENT, "cannot_generate")

        batch = (self.db.scalar(select(func.max(Itinerary.batch)).where(Itinerary.enquiry_id == enquiry_id)) or 0) + 1
        created = [self._store(enquiry, plan, batch, user, inv) for plan in plans]
        self.db.commit()
        return [self.get(i.id) for i in created]

    def _engine_requirements(self, r) -> eng.Requirements:
        return eng.Requirements(
            adults=r.adults, children=r.children, children_ages=list(r.children_ages),
            arrival_date=r.arrival_date, departure_date=r.departure_date,
            arrival_airport=r.arrival_airport, departure_airport=r.departure_airport,
            start_country_id=r.start_country_id, end_country_id=r.end_country_id,
            destinations=[eng.DestinationReq(d.country.id, d.city.id if d.city else None, d.preference, d.min_nights) for d in r.destinations],
            interests=list(r.interests), travel_pace=r.travel_pace, hotel_categories=list(r.hotel_categories),
            hotel_locations=list(r.hotel_locations), breakfast_required=r.breakfast_required,
            rooms=[(x.type, x.count) for x in r.rooms], food_preferences=list(r.food_preferences), meals=list(r.meals),
            transport_modes=list(r.transport_modes), passenger_capacity=r.passenger_capacity,
            airport_transfers=r.airport_transfers, budget_per_person=r.budget_per_person, budget_total=r.budget_total,
            currency=r.currency,
        )

    def _engine_inventory(self) -> eng.Inventory:
        """Snapshot of ACTIVE inventory only (inactive records are never proposed)."""
        cities = {
            c.id: eng.CityInfo(c.id, c.name, c.country_id, c.country.name, c.latitude, c.longitude, c.recommended_nights_min, c.recommended_nights_max)
            for c in self.db.scalars(select(City).options(joinedload(City.country)).where(City.is_active.is_(True)))
            if c.country.is_active
        }
        attractions = [
            eng.AttractionInfo(a.id, a.city_id, a.name, a.category, tuple(a.interest_tags), a.recommended_duration_min,
                               tuple(a.operating_days), a.ticket_required, a.ticket_price, a.currency, a.price_is_verified,
                               a.child_friendly, a.seasonal_info)
            for a in self.db.scalars(select(Attraction).where(Attraction.is_active.is_(True))) if a.city_id in cities
        ]
        hotels = [
            eng.HotelInfo(h.id, h.city_id, h.name, h.star_rating, tuple(h.style_tags), h.location_type, h.breakfast_available,
                          h.group_capacity_rooms,
                          tuple(eng.RoomTypeInfo(rt.id, rt.name, rt.max_occupancy, rt.base_price, rt.currency, rt.price_is_verified) for rt in h.room_types),
                          tuple(eng.RateInfo(r.room_type_id, r.valid_from, r.valid_to, r.price, r.currency, r.is_verified) for r in h.rates),
                          h.is_demo)
            for h in self.db.scalars(select(Hotel).options(selectinload(Hotel.room_types), selectinload(Hotel.rates)).where(Hotel.is_active.is_(True)))
            if h.city_id in cities
        ]
        restaurants = [
            eng.RestaurantInfo(r.id, r.city_id, r.name, r.cuisine, r.vegetarian, r.jain, r.halal, r.vegan, r.non_vegetarian,
                               r.avg_price_per_person, r.currency, r.price_is_verified, r.group_capacity)
            for r in self.db.scalars(select(Restaurant).where(Restaurant.is_active.is_(True))) if r.city_id in cities
        ]
        vehicles = [
            eng.VehicleInfo(v.id, v.name, v.category.code, v.passenger_capacity, tuple(c.id for c in v.operating_countries),
                            v.price_per_day, v.price_per_km, v.driver_cost_per_day, v.currency, v.price_is_verified)
            for v in self.db.scalars(select(Vehicle).options(joinedload(Vehicle.category), selectinload(Vehicle.operating_countries)).where(Vehicle.is_active.is_(True)))
        ]
        countries = {c.country_id: c.country_name for c in cities.values()}
        return eng.Inventory(cities, attractions, hotels, restaurants, vehicles, countries)

    def _store(self, enquiry: Enquiry, plan: eng.Plan, batch: int, user: User, inv: eng.Inventory) -> Itinerary:
        countries = list(dict.fromkeys(inv.cities[c].country_name for c, _ in plan.stops))
        title = f"{plan.title}: {', '.join(countries[:4])}{' +' + str(len(countries) - 4) if len(countries) > 4 else ''} · {plan.total_days} days"
        itinerary = Itinerary(enquiry_id=enquiry.id, title=title[:200], strategy=plan.strategy, batch=batch, created_by_id=user.id)
        version = ItineraryVersion(
            version_number=1, label="Generated", is_locked=True,  # the original proposal is never edited in place
            start_date=plan.days[0].date, total_days=plan.total_days,
            total_nights=plan.total_nights, vehicle_id=plan.vehicle_id, created_by_id=user.id,
            generation_report={
                "strategy": plan.strategy,
                "summary": eng.STRATEGIES[plan.strategy]["summary"],
                "explanations": plan.explanations,
                "warnings": plan.warnings,
                "costs": [{"category": c.category, "description": c.description, "amount": _money(c.amount),
                           "currency": c.currency, "is_estimate": c.is_estimate} for c in plan.costs],
                "total_cost": _money(plan.total_cost),
                "cost_per_person": _money(plan.cost_per_person),
                "currency": plan.currency,
                "unknown_cost_items": plan.unknown_cost_items,
                "total_distance_km": plan.total_distance_km,
                "stops": [{"city_id": c, "nights": n} for c, n in plan.stops],
            },
        )
        for d in plan.days:
            day = ItineraryDay(day_number=d.number, date=d.date, city_id=d.city_id, overnight_city_id=d.overnight_city_id, title=d.title)
            day.activities = [
                ItineraryActivity(sort_order=i, time_slot=a.time_slot, activity_type=a.kind, attraction_id=a.attraction_id,
                                  title=a.title, description=a.description, duration_min=a.duration_min)
                for i, a in enumerate(d.activities)
            ]
            day.meals = [ItineraryMeal(sort_order=i, meal=m.meal, arrangement=m.arrangement, restaurant_id=m.restaurant_id, note=m.note)
                         for i, m in enumerate(d.meals)]
            version.days.append(day)
        version.stays = [
            ItineraryStay(city_id=s.city_id, hotel_id=s.hotel_id, check_in_day=s.check_in_day, nights=s.nights,
                          rooms=[{"room_type_id": rt, "label": label, "count": count, "price": _money(price)} for rt, label, count, price in s.rooms],
                          alternative_hotel_ids=s.alternatives, estimated_cost=s.estimated_cost, note=s.note)
            for s in plan.stays
        ]
        version.transports = [
            ItineraryTransport(day_number=l.day_number, sort_order=i, kind=l.kind, mode=l.mode, from_city_id=l.from_city_id,
                               to_city_id=l.to_city_id, vehicle_id=l.vehicle_id, distance_km=l.distance_km,
                               duration_min=l.duration_min, is_estimate=l.is_estimate, note=l.note)
            for i, l in enumerate(plan.legs)
        ]
        itinerary.versions.append(version)
        self.db.add(itinerary)
        self.db.flush()
        return itinerary

    # -------------------------------------------------------------- reading
    def get(self, itinerary_id: int) -> Itinerary:
        it = self.db.scalar(select(Itinerary).options(selectinload(Itinerary.versions)).where(Itinerary.id == itinerary_id))
        if it is None:
            raise DomainError("Itinerary not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return it

    def list_for_enquiry(self, enquiry_id: int) -> list[Itinerary]:
        return list(self.db.scalars(
            select(Itinerary).options(selectinload(Itinerary.versions))
            .where(Itinerary.enquiry_id == enquiry_id, Itinerary.is_archived.is_(False))
            .order_by(Itinerary.batch.desc(), Itinerary.id)
        ))

    def list_all(self, q: str | None, strategy: str | None, offset: int, limit: int):
        stmt = select(Itinerary).options(selectinload(Itinerary.versions)).where(Itinerary.is_archived.is_(False))
        if strategy:
            stmt = stmt.where(Itinerary.strategy == strategy)
        if q:
            stmt = stmt.outerjoin(Enquiry, Enquiry.id == Itinerary.enquiry_id).where(
                Itinerary.title.ilike(f"%{q.strip()}%") | Enquiry.reference.ilike(f"%{q.strip()}%"))
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        items = list(self.db.scalars(stmt.order_by(Itinerary.created_at.desc(), Itinerary.id.desc()).offset(offset).limit(limit)))
        return items, total

    def current_version(self, itinerary: Itinerary, number: int | None = None) -> ItineraryVersion:
        """Latest version, or a specific `number` (404 if it doesn't exist)."""
        if number is None:
            version = max(itinerary.versions, key=lambda v: v.version_number)
        else:
            version = next((v for v in itinerary.versions if v.version_number == number), None)
            if version is None:
                raise DomainError("Version not found.", status.HTTP_404_NOT_FOUND, "not_found")
        return self.db.scalar(
            select(ItineraryVersion).options(
                selectinload(ItineraryVersion.days).selectinload(ItineraryDay.activities),
                selectinload(ItineraryVersion.days).selectinload(ItineraryDay.meals),
                selectinload(ItineraryVersion.stays), selectinload(ItineraryVersion.transports),
            ).where(ItineraryVersion.id == version.id)
        )
