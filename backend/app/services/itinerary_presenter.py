"""Turn stored itineraries into API views with resolved names and images."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Attraction, City, Enquiry, Hotel, Itinerary, ItineraryVersion, Restaurant, Vehicle
from app.schemas.itinerary import (
    ActivityOut, CostLineOut, DayOut, HotelRef, ItineraryDetail, ItinerarySummary, MealOut, RouteStop, StayOut, TransportOut,
)
from app.services.itinerary_checks import Evaluation, evaluate
from app.services.itinerary_service import ItineraryService
from app.services.media_service import primary_image_urls


class _Lookups:
    def __init__(self, db: Session, city_ids: set[int], hotel_ids: set[int], attraction_ids=frozenset(), restaurant_ids=frozenset(), vehicle_ids=frozenset()):
        self.cities = {c.id: c for c in db.scalars(select(City).options(joinedload(City.country)).where(City.id.in_(city_ids or {0})))}
        self.hotels = {h.id: h for h in db.scalars(select(Hotel).where(Hotel.id.in_(hotel_ids or {0})))}
        self.hotel_images = primary_image_urls(db, "hotel", list(hotel_ids))
        self.attractions = {a.id: a for a in db.scalars(select(Attraction).where(Attraction.id.in_(attraction_ids or {0})))}
        self.attraction_images = primary_image_urls(db, "attraction", list(attraction_ids))
        self.restaurants = {r.id: r for r in db.scalars(select(Restaurant).where(Restaurant.id.in_(restaurant_ids or {0})))}
        self.vehicles = {v.id: v for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids or {0})))}

    def city(self, cid: int | None) -> str | None:
        return self.cities[cid].name if cid in self.cities else None

    def hotel(self, hid: int | None) -> HotelRef | None:
        h = self.hotels.get(hid)
        return HotelRef(id=h.id, name=h.name, stars=h.star_rating, is_demo=h.is_demo, image_url=self.hotel_images.get(h.id)) if h else None


def _route(v: ItineraryVersion, lk: _Lookups) -> list[RouteStop]:
    """Route from the CURRENT stays (so edits are reflected), in order."""
    route = []
    for st in sorted(v.stays, key=lambda x: x.check_in_day):
        c = lk.cities.get(st.city_id)
        if c:
            route.append(RouteStop(city_id=c.id, city=c.name, country=c.country.name, iso_code=c.country.iso_code,
                                   nights=st.nights, lat=c.latitude, lng=c.longitude))
    return route


def _summary(db: Session, it: Itinerary, version: ItineraryVersion, lk: _Lookups, enquiry: Enquiry | None, ev: Evaluation) -> dict:
    rep = version.generation_report or {}
    hotels = [lk.hotel(st.hotel_id) for st in sorted(version.stays, key=lambda x: x.check_in_day)]
    return dict(
        id=it.id, enquiry_id=it.enquiry_id, enquiry_reference=enquiry.reference if enquiry else None,
        customer_name=enquiry.customer.name if enquiry else None, title=it.title, strategy=it.strategy,
        strategy_summary=rep.get("summary", ""), status=it.status, batch=it.batch, created_at=it.created_at,
        version_number=version.version_number, version_label=version.label, version_notes=version.notes,
        is_locked=version.is_locked, latest_version_number=max(x.version_number for x in it.versions),
        start_date=version.start_date, total_days=version.total_days, total_nights=version.total_nights,
        route=_route(version, lk), hotels=hotels,
        total_cost=str(ev.total_cost.quantize(Decimal("1"))), cost_per_person=str(ev.cost_per_person), currency=ev.currency,
        unknown_cost_items=ev.unknown_cost_items, total_distance_km=ev.total_distance_km, warnings_count=len(ev.warnings),
    )


def summaries(db: Session, itineraries: list[Itinerary]) -> list[ItinerarySummary]:
    service = ItineraryService(db)
    versions = {it.id: service.current_version(it) for it in itineraries}
    city_ids = {st.city_id for v in versions.values() for st in v.stays}
    hotel_ids = {s.hotel_id for v in versions.values() for s in v.stays if s.hotel_id}
    lk = _Lookups(db, city_ids, hotel_ids)
    enquiries = {e.id: e for e in db.scalars(select(Enquiry).options(joinedload(Enquiry.customer)).where(Enquiry.id.in_({it.enquiry_id for it in itineraries if it.enquiry_id} or {0})))}
    return [ItinerarySummary(**_summary(db, it, versions[it.id], lk, enquiries.get(it.enquiry_id), evaluate(db, versions[it.id], it.enquiry_id)))
            for it in itineraries]


def detail(db: Session, it: Itinerary, version_number: int | None = None) -> ItineraryDetail:
    v = ItineraryService(db).current_version(it, version_number)
    rep = v.generation_report or {}
    city_ids = {d.city_id for d in v.days} | {d.overnight_city_id for d in v.days if d.overnight_city_id} | {s.city_id for s in v.stays} \
        | {t.from_city_id for t in v.transports if t.from_city_id} | {t.to_city_id for t in v.transports if t.to_city_id} \

    hotel_ids = {s.hotel_id for s in v.stays if s.hotel_id} | {h for s in v.stays for h in s.alternative_hotel_ids}
    attraction_ids = {a.attraction_id for d in v.days for a in d.activities if a.attraction_id}
    restaurant_ids = {m.restaurant_id for d in v.days for m in d.meals if m.restaurant_id}
    vehicle_ids = {t.vehicle_id for t in v.transports if t.vehicle_id} | ({v.vehicle_id} if v.vehicle_id else set())
    lk = _Lookups(db, city_ids, hotel_ids, attraction_ids, restaurant_ids, vehicle_ids)
    enquiry = db.scalar(select(Enquiry).options(joinedload(Enquiry.customer)).where(Enquiry.id == it.enquiry_id)) if it.enquiry_id else None

    days = [
        DayOut(
            id=d.id, day_number=d.day_number, date=d.date, city_id=d.city_id, city=lk.city(d.city_id) or "", overnight_city=lk.city(d.overnight_city_id),
            title=d.title, description=d.description,
            activities=[ActivityOut(id=a.id, time_slot=a.time_slot, activity_type=a.activity_type, title=a.title, description=a.description,
                                    duration_min=a.duration_min, attraction_id=a.attraction_id,
                                    image_url=lk.attraction_images.get(a.attraction_id) if a.attraction_id else None) for a in d.activities],
            meals=[MealOut(id=m.id, meal=m.meal, arrangement=m.arrangement, restaurant_id=m.restaurant_id,
                           restaurant_name=lk.restaurants[m.restaurant_id].name if m.restaurant_id in lk.restaurants else None,
                           cuisine=lk.restaurants[m.restaurant_id].cuisine if m.restaurant_id in lk.restaurants else None, note=m.note)
                   for m in d.meals],
        )
        for d in v.days
    ]
    stays = [
        StayOut(id=s.id, city_id=s.city_id, city=lk.city(s.city_id) or "", check_in_day=s.check_in_day, nights=s.nights,
                hotel=lk.hotel(s.hotel_id), rooms=s.rooms, alternatives=[h for h in (lk.hotel(x) for x in s.alternative_hotel_ids) if h],
                estimated_cost=None if s.estimated_cost is None else str(s.estimated_cost), note=s.note)
        for s in v.stays
    ]
    transports = [
        TransportOut(id=t.id, day_number=t.day_number, kind=t.kind, mode=t.mode, from_city=lk.city(t.from_city_id), to_city=lk.city(t.to_city_id),
                     vehicle=lk.vehicles[t.vehicle_id].name if t.vehicle_id in lk.vehicles else None, distance_km=t.distance_km,
                     duration_min=t.duration_min, is_estimate=t.is_estimate, note=t.note)
        for t in v.transports
    ]
    ev = evaluate(db, v, it.enquiry_id)
    base = _summary(db, it, v, lk, enquiry, ev)
    return ItineraryDetail(
        **base,
        explanations=rep.get("explanations", []), warnings=ev.warnings,
        costs=[CostLineOut(**c) for c in ev.costs],
        vehicle=lk.vehicles[v.vehicle_id].name if v.vehicle_id in lk.vehicles else None,
        days=days, stays=stays, transports=transports,
    )
