"""Import an itinerary template from a structured description (Phase 8d).

Used to turn an existing brochure (e.g. YANA's "European Grand Tour" reference
PDF) into a reusable template. The JSON names cities, sightseeing and meals per
day; cities and sightseeing are matched to inventory by name. Missing cities or
sightseeing can be created when the file gives their details (e.g. Cochem with
coordinates). Unknown sightseeing becomes a custom activity and is reported.
The PDF wording from the brochure goes into the template's PDF settings
(`day_texts`), so proposals made from the template read like the original.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError
from app.models import (
    Attraction, City, Country, Hotel, Itinerary, ItineraryActivity, ItineraryDay, ItineraryMeal, ItineraryTransport, ItineraryVersion,
    Restaurant, User, Vehicle,
)
from app.schemas.proposal import ProposalSettings
from app.services.itinerary_editor import ItineraryEditor

SLOTS = ("morning", "afternoon", "full_day", "evening")


class NewCity(BaseModel):
    name: str
    country: str = Field(description="ISO code, e.g. DE")
    lat: float
    lng: float


class NewAttraction(BaseModel):
    city: str
    name: str
    category: str = "landmark"
    ticket_required: bool = False
    description: str | None = None


class PlanActivity(BaseModel):
    attraction: str | None = None  # inventory name (matched in the day's city)
    custom: str | None = None  # free text when not in inventory
    slot: str = "morning"


class PlanDay(BaseModel):
    city: str
    overnight: str | None = None  # None on the departure day
    title: str
    description: str | None = None
    activities: list[PlanActivity] = Field(default_factory=list)
    meals: dict[str, str] = Field(default_factory=dict)  # breakfast/lunch/dinner -> hotel / restaurant / own


class TemplatePlan(BaseModel):
    title: str
    description: str | None = None
    strategy: str = "classic"
    start_date: date
    group_size: int = 2
    vehicle: str | None = None  # part of a vehicle name, e.g. "touring coach"
    hotel_stars: int | None = 4
    rooms: list[dict] = Field(default_factory=lambda: [{"label": "Double", "count": 1}])
    arrival_airport: str | None = None
    departure_airport: str | None = None
    create_cities: list[NewCity] = Field(default_factory=list)
    create_attractions: list[NewAttraction] = Field(default_factory=list)
    days: list[PlanDay] = Field(min_length=2)
    pdf: dict = Field(default_factory=dict)  # ProposalSettings fields (title, intro, closing, day_texts...)


def import_template(db: Session, user: User, plan: TemplatePlan) -> tuple[Itinerary, list[str]]:
    notes: list[str] = []
    countries = {c.iso_code.upper(): c for c in db.scalars(select(Country))}

    def city_by_name(name: str) -> City | None:
        return db.scalar(select(City).where(City.name.ilike(name.strip())))

    for nc in plan.create_cities:
        if city_by_name(nc.name) is None:
            country = countries.get(nc.country.upper())
            if country is None:
                raise DomainError(f"Country {nc.country} is not in inventory.", status.HTTP_400_BAD_REQUEST, "unknown_country")
            db.add(City(country_id=country.id, name=nc.name, latitude=nc.lat, longitude=nc.lng))
            notes.append(f"Added city {nc.name} ({country.name}) to inventory.")
    db.flush()
    for na in plan.create_attractions:
        city = city_by_name(na.city)
        if city and db.scalar(select(Attraction).where(Attraction.city_id == city.id, Attraction.name.ilike(na.name))) is None:
            db.add(Attraction(city_id=city.id, name=na.name, category=na.category, ticket_required=na.ticket_required,
                              description=na.description, interest_tags=[], operating_days=[]))
            notes.append(f"Added sightseeing {na.name} ({city.name}) to inventory.")
    db.flush()

    missing = sorted({n for d in plan.days for n in (d.city, d.overnight) if n and city_by_name(n) is None})
    if missing:
        raise DomainError("Cities not in inventory: " + ", ".join(missing) + ". Add them (or list them under create_cities).",
                          status.HTTP_400_BAD_REQUEST, "unknown_city")

    vehicle = None
    if plan.vehicle:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.name.ilike(f"%{plan.vehicle}%"), Vehicle.is_active.is_(True)))
        if vehicle is None:
            notes.append(f"No active vehicle matching “{plan.vehicle}”; choose one in the builder.")

    pdf = ProposalSettings.model_validate(plan.pdf)
    it = Itinerary(enquiry_id=None, kind="template", title=plan.title[:200], strategy=plan.strategy, status="template", batch=1,
                   created_by_id=user.id, proposal_settings=pdf.model_dump(mode="json"))
    db.add(it)
    db.flush()
    n = len(plan.days)
    v = ItineraryVersion(itinerary_id=it.id, version_number=1, label="Template", notes=plan.description, start_date=plan.start_date,
                         total_days=n, total_nights=n - 1, vehicle_id=vehicle.id if vehicle else None, generation_report={},
                         is_locked=False, created_by_id=user.id)
    prev_overnight = None
    for i, pd in enumerate(plan.days):
        city = city_by_name(pd.city)
        overnight = city_by_name(pd.overnight) if pd.overnight else None
        day = ItineraryDay(day_number=i + 1, date=plan.start_date + timedelta(days=i), city_id=city.id,
                           overnight_city_id=overnight.id if overnight else None, title=pd.title, description=pd.description)
        acts: list[ItineraryActivity] = []
        if i == 0:
            acts.append(ItineraryActivity(time_slot="morning", activity_type="arrival", title=f"Arrive at {plan.arrival_airport or city.name}",
                                          description="Meet and greet; private transfer to the hotel."))
        elif prev_overnight and overnight and overnight.id != prev_overnight.id or (i == n - 1 and prev_overnight):
            acts.append(ItineraryActivity(time_slot="morning", activity_type="check_out", title=f"Check out in {prev_overnight.name}"))
        for a in pd.activities:
            slot = a.slot if a.slot in SLOTS else "morning"
            att = None
            if a.attraction:
                att = db.scalar(select(Attraction).where(Attraction.city_id == city.id, Attraction.name.ilike(a.attraction)))
                if att is None:
                    att = db.scalar(select(Attraction).where(Attraction.name.ilike(a.attraction)))
                if att is None:
                    notes.append(f"Day {i + 1}: “{a.attraction}” is not in inventory; added as a custom activity.")
            if att:
                acts.append(ItineraryActivity(time_slot=slot, activity_type="sightseeing", attraction_id=att.id, title=att.name,
                                              duration_min=att.recommended_duration_min))
            else:
                acts.append(ItineraryActivity(time_slot=slot, activity_type="sightseeing", title=a.custom or a.attraction or "Sightseeing"))
        if overnight and (prev_overnight is None or overnight.id != prev_overnight.id):
            acts.append(ItineraryActivity(time_slot="afternoon", activity_type="check_in", title=f"Hotel check-in in {overnight.name}"))
        if i == n - 1:
            acts.append(ItineraryActivity(time_slot="morning", activity_type="departure", title=f"Transfer to {plan.departure_airport or city.name}",
                                          description="End of services."))
        for k, act in enumerate(acts):
            act.sort_order = k
        day.activities = acts
        meal_city = overnight or city
        for k, meal in enumerate(("breakfast", "lunch", "dinner")):
            arrangement = pd.meals.get(meal)
            if not arrangement:
                continue
            rid = None
            if arrangement == "restaurant":
                rests = list(db.scalars(select(Restaurant).where(Restaurant.city_id.in_({city.id, meal_city.id}), Restaurant.is_active.is_(True))))
                pick = next((r for r in rests if r.cuisine and "indian" in r.cuisine.lower()), None) or (rests[0] if rests else None)
                rid = pick.id if pick else None
            day.meals.append(ItineraryMeal(sort_order=k, meal=meal, arrangement=arrangement, restaurant_id=rid))
        v.days.append(day)
        prev_overnight = overnight or prev_overnight
    first, last = city_by_name(plan.days[0].overnight or plan.days[0].city), city_by_name(plan.days[-1].city)
    v.transports = [
        ItineraryTransport(day_number=1, sort_order=0, kind="airport_transfer", mode="coach", from_city_id=None, to_city_id=first.id,
                           vehicle_id=v.vehicle_id, note=f"From {plan.arrival_airport}" if plan.arrival_airport else None),
        ItineraryTransport(day_number=n, sort_order=1, kind="airport_transfer", mode="coach", from_city_id=last.id, to_city_id=None,
                           vehicle_id=v.vehicle_id, note=f"To {plan.departure_airport}" if plan.departure_airport else None),
    ]
    db.add(v)
    db.flush()

    editor = ItineraryEditor(db, user)
    editor._rebuild(v)  # stays from the overnight cities, legs between cities (incl. cities on the way)
    for s in v.stays:
        hotels = list(db.scalars(select(Hotel).options(selectinload(Hotel.room_types), selectinload(Hotel.rates))
                                 .where(Hotel.city_id == s.city_id, Hotel.is_active.is_(True))))
        hotels.sort(key=lambda h: (abs((h.star_rating or 0) - (plan.hotel_stars or 4)), h.name))
        check_in = plan.start_date + timedelta(days=s.check_in_day - 1)
        if hotels:
            s.hotel_id = hotels[0].id
            s.alternative_hotel_ids = [h.id for h in hotels[1:4]]
            s.rooms = editor._map_rooms(hotels[0], plan.rooms, check_in)
            s.estimated_cost = editor._stay_cost(s)
            s.note = None
        else:
            notes.append(f"No hotel in inventory for {db.get(City, s.city_id).name}; choose one in the builder.")
    v.is_locked = True
    db.commit()
    return it, notes
