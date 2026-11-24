"""Live validation and cost estimate of an itinerary version (PRD 13.4, 14).

Recomputed from the version's CURRENT content every time it is viewed, so
edits are always re-checked. Nothing here changes data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Attraction, City, Enquiry, Hotel, ItineraryVersion, Restaurant, Vehicle
from app.services.requirement_service import RequirementService

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DIET_FLAGS = {"indian_vegetarian": ("vegetarian", "Indian vegetarian"), "indian_jain": ("jain", "Jain"),
              "halal": ("halal", "Halal"), "vegan": ("vegan", "Vegan")}
MAX_SIGHTSEEING_MIN = 540


@dataclass
class Evaluation:
    costs: list[dict] = field(default_factory=list)
    total_cost: Decimal = Decimal(0)
    cost_per_person: Decimal = Decimal(0)
    currency: str = "EUR"
    unknown_cost_items: int = 0
    total_distance_km: int = 0
    warnings: list[str] = field(default_factory=list)
    travellers: int = 1


def _money(v) -> str | None:
    return None if v is None else str(Decimal(v).quantize(Decimal("1")))


def evaluate(db: Session, v: ItineraryVersion, enquiry_id: int | None) -> Evaluation:
    ev = Evaluation()
    req = RequirementService(db).get(enquiry_id) if enquiry_id else None
    enquiry = db.get(Enquiry, enquiry_id) if enquiry_id else None
    ev.travellers = req.total_travellers if req else (enquiry.total_travellers if enquiry else 1) or 1
    ev.currency = req.currency if req else "EUR"
    w = ev.warnings

    days = sorted(v.days, key=lambda d: d.day_number)
    attraction_ids = {a.attraction_id for d in days for a in d.activities if a.attraction_id}
    restaurant_ids = {m.restaurant_id for d in days for m in d.meals if m.restaurant_id}
    hotel_ids = {s.hotel_id for s in v.stays if s.hotel_id}
    attractions = {a.id: a for a in db.scalars(select(Attraction).where(Attraction.id.in_(attraction_ids or {0})))}
    restaurants = {r.id: r for r in db.scalars(select(Restaurant).where(Restaurant.id.in_(restaurant_ids or {0})))}
    hotels = {h.id: h for h in db.scalars(select(Hotel).where(Hotel.id.in_(hotel_ids or {0})))}
    city_ids = {d.city_id for d in days} | {s.city_id for s in v.stays}
    cities = {c.id: c for c in db.scalars(select(City).options(selectinload(City.country)).where(City.id.in_(city_ids or {0})))}
    vehicle = db.scalar(select(Vehicle).options(selectinload(Vehicle.operating_countries)).where(Vehicle.id == v.vehicle_id)) if v.vehicle_id else None
    name = lambda cid: cities[cid].name if cid in cities else "?"  # noqa: E731

    # ------------------------------------------------------------- sightseeing
    seen: dict[int, int] = {}
    for d in days:
        weekday = WEEKDAYS[d.date.weekday()]
        minutes = 0
        for a in d.activities:
            if not a.attraction_id:
                continue
            att = attractions.get(a.attraction_id)
            minutes += a.duration_min or (att.recommended_duration_min if att else 0) or 0
            if att is None:
                continue
            if a.attraction_id in seen:
                w.append(f"{att.name} is scheduled on day {seen[a.attraction_id]} and again on day {d.day_number}.")
            seen.setdefault(a.attraction_id, d.day_number)
            if not att.is_active:
                w.append(f"Day {d.day_number}: {att.name} is no longer active in inventory.")
            if att.city_id != d.city_id:
                w.append(f"Day {d.day_number}: {att.name} is in {name(att.city_id)}, not {name(d.city_id)}.")
            if att.operating_days and weekday not in att.operating_days:
                w.append(f"Day {d.day_number} ({d.date:%a}): {att.name} is closed on that weekday.")
            if req and req.children and att.child_friendly is False:
                w.append(f"Day {d.day_number}: {att.name} is marked unsuitable for children.")
        if minutes > MAX_SIGHTSEEING_MIN:
            w.append(f"Day {d.day_number} has about {minutes // 60} h of sightseeing; it may be too busy.")

    # ------------------------------------------------------------- meals
    needed = [DIET_FLAGS[f] for f in (req.food_preferences if req else []) if f in DIET_FLAGS]
    to_arrange = []
    for d in days:
        for m in d.meals:
            if m.arrangement == "restaurant":
                r = restaurants.get(m.restaurant_id)
                if r is None:
                    continue
                if not r.is_active:
                    w.append(f"Day {d.day_number} {m.meal}: {r.name} is no longer active in inventory.")
                missing = [label for flag, label in needed if getattr(r, flag) is not True]
                if missing:
                    w.append(f"Day {d.day_number} {m.meal}: {r.name} has no verified {', '.join(missing)} option.")
            elif m.arrangement == "own" and m.meal != "breakfast":
                to_arrange.append(f"{d.day_number} {m.meal}")
    if to_arrange:
        w.append(f"{len(to_arrange)} meal(s) still to be arranged (days {', '.join(sorted({x.split()[0] for x in to_arrange}, key=int))}).")

    # ------------------------------------------------------------- hotels
    wanted = {int(c[0]) for c in (req.hotel_categories if req else []) if c.endswith("_star")}
    for s in v.stays:
        h = hotels.get(s.hotel_id)
        if h is None:
            w.append(f"No hotel selected in {name(s.city_id)} (days {s.check_in_day}–{s.check_in_day + s.nights - 1}).")
            continue
        if not h.is_active:
            w.append(f"{h.name} is no longer active in inventory.")
        if wanted and h.star_rating and h.star_rating < min(wanted):
            w.append(f"{h.name} ({h.star_rating}★) is below the requested {min(wanted)}★.")

    # ------------------------------------------------------------- transport
    countries = {cities[c].country_id for c in city_ids if c in cities}
    if vehicle:
        if vehicle.passenger_capacity < ev.travellers:
            w.append(f"{vehicle.name} has {vehicle.passenger_capacity} seats for {ev.travellers} travellers.")
        if not vehicle.is_active:
            w.append(f"{vehicle.name} is no longer active in inventory.")
        ops = {c.id for c in vehicle.operating_countries}
        if ops and countries - ops:
            missing = sorted(cities[c].country.name for c in city_ids if c in cities and cities[c].country_id in countries - ops)
            w.append(f"{vehicle.name} is not listed as operating in: {', '.join(dict.fromkeys(missing))}.")
    else:
        w.append("No vehicle assigned.")
    for t in v.transports:
        if t.kind == "intercity":
            ev.total_distance_km += t.distance_km or 0
            if t.mode != "train" and t.duration_min and t.duration_min > 360:
                w.append(f"Day {t.day_number}: {name(t.from_city_id)} → {name(t.to_city_id)} is about {t.duration_min // 60} h by road (estimate).")

    # ------------------------------------------------------------- costs (estimates)
    lines = ev.costs
    for s in sorted(v.stays, key=lambda s: s.check_in_day):
        h = hotels.get(s.hotel_id)
        lines.append({"category": "hotel", "description": f"{h.name if h else 'Hotel to be selected'}, {name(s.city_id)}, {s.nights} night{'s' if s.nights != 1 else ''}",
                      "amount": _money(s.estimated_cost), "currency": ev.currency, "is_estimate": True})
    if vehicle:
        if vehicle.price_per_day is not None:
            amount = (vehicle.price_per_day + (vehicle.driver_cost_per_day or 0)) * v.total_days
        elif vehicle.price_per_km is not None:
            amount = vehicle.price_per_km * ev.total_distance_km
        else:
            amount = None
        lines.append({"category": "transport", "description": f"{vehicle.name}, {v.total_days} days incl. driver", "amount": _money(amount),
                      "currency": vehicle.currency, "is_estimate": True})
    for t in v.transports:
        if t.mode == "train":
            lines.append({"category": "transport", "description": f"Train {name(t.from_city_id)} → {name(t.to_city_id)}", "amount": None,
                          "currency": ev.currency, "is_estimate": True})
    for aid in sorted(seen):
        a = attractions[aid]
        if a.ticket_required:
            amount = a.ticket_price * ev.travellers if a.ticket_price is not None else None
            lines.append({"category": "sightseeing", "description": f"{a.name} tickets × {ev.travellers}", "amount": _money(amount),
                          "currency": a.currency, "is_estimate": True})
    counts: dict[int, int] = {}
    for d in days:
        for m in d.meals:
            if m.arrangement == "restaurant" and m.restaurant_id in restaurants:
                counts[m.restaurant_id] = counts.get(m.restaurant_id, 0) + 1
    for rid, n in sorted(counts.items()):
        r = restaurants[rid]
        amount = r.avg_price_per_person * ev.travellers * n if r.avg_price_per_person is not None else None
        lines.append({"category": "meals", "description": f"{r.name}: {n} meal{'s' if n != 1 else ''} × {ev.travellers}", "amount": _money(amount),
                      "currency": r.currency, "is_estimate": True})

    ev.unknown_cost_items = sum(1 for c in lines if c["amount"] is None)
    ev.total_cost = sum((Decimal(c["amount"]) for c in lines if c["amount"] is not None and c["currency"] == ev.currency), Decimal(0))
    ev.cost_per_person = (ev.total_cost / ev.travellers).quantize(Decimal("1"))
    if ev.unknown_cost_items:
        w.append(f"{ev.unknown_cost_items} cost item(s) have no price in inventory: the estimate is incomplete.")
    if req:
        budget = req.budget_total or (req.budget_per_person * ev.travellers if req.budget_per_person is not None else None)
        if budget and ev.total_cost > budget:
            w.append(f"Estimated cost {ev.total_cost:,.0f} {ev.currency} is {(ev.total_cost - budget) / budget * 100:.0f}% over the budget of {budget:,.0f} {ev.currency}.")
    return ev
