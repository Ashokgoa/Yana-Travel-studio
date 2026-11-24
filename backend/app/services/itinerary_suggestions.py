"""Itinerary suggestions (Phase 8): reviewable improvements, from inventory only.

Rules look at the itinerary and the customer's requirements and propose single
changes (remove a duplicate, move a visit off a closed day, use a restaurant
with a verified diet option, fill a free day with matching sightseeing, use a
hotel of the requested category). Each suggestion has a stable key so it can be
applied later, and applying goes through the builder's normal edit operations
on a working copy, so it is versioned like any manual edit. Nothing changes
until the planner clicks Apply.
"""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Attraction, City, Hotel, Itinerary, ItineraryVersion, Restaurant, User
from app.services.itinerary_editor import ItineraryEditor
from app.services.itinerary_service import ItineraryService
from app.services.requirement_service import RequirementService

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DIET_FLAGS = {"indian_vegetarian": ("vegetarian", "vegetarian"), "indian_jain": ("jain", "Jain"), "halal": ("halal", "halal"), "vegan": ("vegan", "vegan")}


class Suggestion(BaseModel):
    key: str
    kind: str  # duplicate / closed_day / children / diet / free_day / hotel_category
    title: str
    reason: str
    action: dict  # what Apply will do (op + parameters), for transparency


def _suggest(db: Session, it: Itinerary, v: ItineraryVersion) -> list[Suggestion]:
    req = RequirementService(db).get(it.enquiry_id) if it.enquiry_id else None
    days = sorted(v.days, key=lambda d: d.day_number)
    city_ids = {d.city_id for d in days} | {s.city_id for s in v.stays}
    cities = {c.id: c for c in db.scalars(select(City).where(City.id.in_(city_ids or {0})))}
    attractions = {a.id: a for a in db.scalars(select(Attraction).where(Attraction.city_id.in_(city_ids or {0})))}
    used = {a.attraction_id for d in days for a in d.activities if a.attraction_id}
    out: list[Suggestion] = []
    interests = set(req.interests) if req else set()
    children = bool(req and req.children)

    # ------------------------------------------------------------ sightseeing
    seen: dict[int, int] = {}
    for d in days:
        weekday = WEEKDAYS[d.date.weekday()]
        for a in d.activities:
            att = attractions.get(a.attraction_id) if a.attraction_id else None
            if att is None:
                continue
            if a.attraction_id in seen:
                out.append(Suggestion(key=f"duplicate:{att.id}:{d.day_number}", kind="duplicate", title=f"Remove the second visit to {att.name} (day {d.day_number})",
                                      reason=f"It is already on day {seen[att.id]}.", action={"op": "remove_activity", "day": d.day_number, "attraction_id": att.id}))
                continue
            seen[att.id] = d.day_number
            if att.operating_days and weekday not in att.operating_days:
                other = next((x for x in days if x.city_id == att.city_id and x.day_number != d.day_number and x.overnight_city_id
                              and WEEKDAYS[x.date.weekday()] in att.operating_days), None)
                if other:
                    out.append(Suggestion(key=f"closed_day:{att.id}:{d.day_number}", kind="closed_day",
                                          title=f"Move {att.name} from day {d.day_number} to day {other.day_number}",
                                          reason=f"It is closed on {d.date:%A}s; open on {other.date:%A}.",
                                          action={"op": "move_activity", "day": d.day_number, "attraction_id": att.id, "to_day": other.day_number}))
                else:
                    out.append(Suggestion(key=f"closed_day:{att.id}:{d.day_number}", kind="closed_day", title=f"Remove {att.name} from day {d.day_number}",
                                          reason=f"It is closed on {d.date:%A}s and there is no other day in {cities[att.city_id].name} when it is open.",
                                          action={"op": "remove_activity", "day": d.day_number, "attraction_id": att.id}))
            elif children and att.child_friendly is False:
                out.append(Suggestion(key=f"children:{att.id}:{d.day_number}", kind="children", title=f"Remove {att.name} from day {d.day_number}",
                                      reason="It is marked unsuitable for children, and this group has children.",
                                      action={"op": "remove_activity", "day": d.day_number, "attraction_id": att.id}))

    # ------------------------------------------------------------ free days
    for d in days:
        free = next((a for a in d.activities if a.activity_type == "free_time" and a.time_slot == "full_day"), None)
        if free is None or not d.overnight_city_id:
            continue
        weekday = WEEKDAYS[d.date.weekday()]
        options = [a for a in attractions.values() if a.city_id == d.city_id and a.is_active and a.id not in used
                   and (not a.operating_days or weekday in a.operating_days) and not (children and a.child_friendly is False)]
        options.sort(key=lambda a: (-len(interests & set(a.interest_tags or [])), a.name))
        if options:
            best = options[0]
            match = sorted(interests & set(best.interest_tags or []))
            why = f"matches the interests: {', '.join(m.replace('_', ' ') for m in match)}" if match else "not yet in this itinerary"
            out.append(Suggestion(key=f"free_day:{d.day_number}:{best.id}", kind="free_day", title=f"Add {best.name} to the free day {d.day_number} in {cities[d.city_id].name}",
                                  reason=f"Day {d.day_number} is a free day; {best.name} is open on {d.date:%A}s and {why}. The rest of the day stays free.",
                                  action={"op": "add_activity", "day": d.day_number, "attraction_id": best.id}))
            used.add(best.id)

    # ------------------------------------------------------------ meals and diet
    needed = [DIET_FLAGS[f] for f in (req.food_preferences if req else []) if f in DIET_FLAGS]
    if needed:
        rest_ids = {m.restaurant_id for d in days for m in d.meals if m.restaurant_id}
        city_rests = list(db.scalars(select(Restaurant).where(Restaurant.city_id.in_(city_ids or {0}), Restaurant.is_active.is_(True))))
        rests = {r.id: r for r in city_rests} | {r.id: r for r in db.scalars(select(Restaurant).where(Restaurant.id.in_(rest_ids or {0})))}
        for d in days:
            for m in d.meals:
                r = rests.get(m.restaurant_id) if m.arrangement == "restaurant" else None
                if r is None:
                    continue
                missing = [label for flag, label in needed if getattr(r, flag) is not True]
                if not missing:
                    continue
                better = next((x for x in city_rests if x.city_id == d.city_id and x.id != r.id and all(getattr(x, flag) is True for flag, _ in needed)), None)
                if better:
                    out.append(Suggestion(key=f"diet:{d.day_number}:{m.meal}:{better.id}", kind="diet",
                                          title=f"Day {d.day_number} {m.meal}: use {better.name} instead of {r.name}",
                                          reason=f"{r.name} has no verified {', '.join(missing)} option; {better.name} does.",
                                          action={"op": "set_meal", "day": d.day_number, "meal": m.meal, "restaurant_id": better.id}))

    # ------------------------------------------------------------ hotel category
    wanted = sorted(int(c[0]) for c in (req.hotel_categories if req else []) if c.endswith("_star"))
    if wanted:
        stays_hotels = {h.id: h for h in db.scalars(select(Hotel).where(Hotel.city_id.in_({s.city_id for s in v.stays} or {0}), Hotel.is_active.is_(True)))}
        for s in v.stays:
            h = stays_hotels.get(s.hotel_id) or (db.get(Hotel, s.hotel_id) if s.hotel_id else None)
            if h and h.star_rating and h.star_rating >= wanted[0]:
                continue
            better = sorted((x for x in stays_hotels.values() if x.city_id == s.city_id and (x.star_rating or 0) >= wanted[0]),
                            key=lambda x: (abs((x.star_rating or 0) - wanted[0]), x.name))
            if better:
                b = better[0]
                now = f"{h.name} ({h.star_rating}★)" if h else "no hotel"
                out.append(Suggestion(key=f"hotel_category:{s.check_in_day}:{b.id}", kind="hotel_category",
                                      title=f"Use {b.name} ({b.star_rating}★) in {cities[s.city_id].name}",
                                      reason=f"The customer asked for {wanted[0]}★ or better; the itinerary has {now}.",
                                      action={"op": "replace_hotel", "check_in_day": s.check_in_day, "hotel_id": b.id}))
    return out


def suggestions(db: Session, itinerary_id: int, version_number: int | None = None) -> list[Suggestion]:
    svc = ItineraryService(db)
    it = svc.get(itinerary_id)
    return _suggest(db, it, svc.current_version(it, version_number))


def apply(db: Session, user: User, itinerary_id: int, key: str) -> None:
    """Apply one suggestion to the working copy (created from the latest version if needed)."""
    editor = ItineraryEditor(db, user)
    editor.start_editing(itinerary_id)
    svc = ItineraryService(db)
    it = svc.get(itinerary_id)
    v = svc.current_version(it)
    s = next((x for x in _suggest(db, it, v) if x.key == key), None)
    if s is None:
        raise DomainError("This suggestion no longer applies. The list has been refreshed.", 409, "suggestion_stale")
    a = s.action
    day = next(d for d in v.days if d.day_number == a.get("day", a.get("check_in_day")))
    if a["op"] in ("remove_activity", "move_activity"):
        # The later duplicate is the last matching activity of that day.
        act = [x for x in day.activities if x.attraction_id == a["attraction_id"]][-1]
        if a["op"] == "remove_activity":
            editor.remove_activity(itinerary_id, act.id)
        else:
            target = next(d for d in v.days if d.day_number == a["to_day"])
            editor.move_activity(itinerary_id, act.id, a["to_day"], len(target.activities), None)
    elif a["op"] == "add_activity":
        editor.add_activity(itinerary_id, a["day"], time_slot="afternoon", attraction_id=a["attraction_id"], activity_type="sightseeing",
                            title=None, description=None, duration_min=None)
    elif a["op"] == "set_meal":
        editor.set_meal(itinerary_id, a["day"], a["meal"], "restaurant", a["restaurant_id"], None)
    elif a["op"] == "replace_hotel":
        stay = next(x for x in v.stays if x.check_in_day == a["check_in_day"])
        editor.replace_hotel(itinerary_id, stay.id, a["hotel_id"])
