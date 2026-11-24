"""Read requirements from text (Phase 8): provider output -> reviewable suggestions.

Each suggestion is one field with the proposed value in the requirement form's
own format, a readable description, the quote it came from, and whether it
would overwrite something already entered. The planner chooses what to apply in
the wizard; this service never saves anything.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import City, Country
from app.services.ai_provider import AIUnavailable, OfflineProvider, get_provider
from app.services.requirement_service import RequirementService

LABELS = {
    "indian_vegetarian": "Indian vegetarian", "indian_jain": "Jain", "indian_non_vegetarian": "Indian non-vegetarian", "halal": "Halal",
    "vegan": "Vegan", "continental": "Continental", "mixed": "Mixed", "private_coach": "Private coach", "luxury_coach": "Luxury coach",
    "mini_bus": "Minibus", "private_car": "Private car", "train": "Train", "3_star": "3★", "4_star": "4★", "5_star": "5★",
}


class FieldSuggestion(BaseModel):
    field: str
    label: str
    value: object
    display: str
    merge: str  # replace / union / append
    evidence: str | None = None
    current: str | None = None
    overwrites: bool = False


class ReadResult(BaseModel):
    provider: str
    provider_label: str
    sends_data_off_device: bool
    fallback_note: str | None = None
    suggestions: list[FieldSuggestion]
    unmatched_places: list[str]
    special_requests: list[str]


def _nice(v: str) -> str:
    return LABELS.get(v, v.replace("_", " ").capitalize())


class AIService:
    def __init__(self, db: Session):
        self.db = db

    def read_requirements(self, enquiry_id: int, text: str, today: date | None = None) -> ReadResult:
        today = today or date.today()
        current = RequirementService(self.db).get(enquiry_id)
        countries = list(self.db.scalars(select(Country).where(Country.is_active.is_(True))))
        cities = list(self.db.scalars(select(City).options(joinedload(City.country)).where(City.is_active.is_(True))))
        provider = get_provider()
        note = None
        kwargs = dict(today=today, known_countries=[c.name for c in countries], known_cities=[c.name for c in cities])
        try:
            found = provider.extract_requirements(text, **kwargs)
        except AIUnavailable as exc:
            note = f"{exc} The offline reader was used instead."
            provider = OfflineProvider()
            found = provider.extract_requirements(text, **kwargs)

        evidence = {e.field: e.text for e in found.evidence}
        out: list[FieldSuggestion] = []

        def add(field, label, value, display, merge="replace", source=None, current_value=None, current_display=None):
            empty = current_value in (None, [], "", 0) or (field == "adults" and current_value == 1 and not current.completed_steps)
            same = current_value == value or (merge == "union" and isinstance(value, list) and set(value) <= set(current_value or []))
            if same:
                return
            out.append(FieldSuggestion(field=field, label=label, value=value, display=display, merge=merge,
                                       evidence=evidence.get(source or field), current=None if empty else current_display,
                                       overwrites=not empty and merge == "replace"))

        if found.adults is not None:
            add("adults", "Adults", found.adults, str(found.adults), current_value=current.adults, current_display=str(current.adults))
        if found.children is not None:
            add("children", "Children", found.children, str(found.children), current_value=current.children, current_display=str(current.children))
        if found.children_ages:
            add("children_ages", "Children's ages", found.children_ages, ", ".join(map(str, found.children_ages)),
                current_value=current.children_ages, current_display=", ".join(map(str, current.children_ages)))
        for field, label in (("arrival_date", "Arrival date"), ("departure_date", "Departure date")):
            v = getattr(found, field)
            if v:
                cur = getattr(current, field)
                add(field, label, v.isoformat(), f"{v:%d %b %Y}", current_value=cur.isoformat() if cur else None,
                    current_display=f"{cur:%d %b %Y}" if cur else None)

        def match_city(name: str | None) -> City | None:
            if not name:
                return None
            n = name.lower().replace("airport", "").strip()
            return next((c for c in cities if c.name.lower() == n or n.startswith(c.name.lower())), None)

        for place, field, cfield, label in ((found.arrival_place, "arrival_airport", "start_country_id", "Arrival"),
                                            (found.departure_place, "departure_airport", "end_country_id", "Departure")):
            if not place:
                continue
            city = match_city(place)
            text_value = city.name if city else place
            add(field, f"{label} city / airport", text_value, text_value, source=field.replace("airport", "place"),
                current_value=getattr(current, field), current_display=getattr(current, field))
            if city:
                cur = getattr(current, cfield)
                add(cfield, f"{label} country", city.country_id, city.country.name, source=field.replace("airport", "place"),
                    current_value=cur, current_display=next((c.name for c in countries if c.id == cur), None))

        # Destinations: matched cities (with their country) plus countries without a matched city.
        unmatched: list[str] = []
        by_name = {c.name.lower(): c for c in countries}
        dests, shown = [], []
        city_countries = set()
        for name in found.cities:
            c = match_city(name)
            if c is None:
                unmatched.append(name)
                continue
            if all(d["city_id"] != c.id for d in dests):
                dests.append({"country_id": c.country_id, "city_id": c.id, "preference": "mandatory", "min_nights": None})
                shown.append(f"{c.name} ({c.country.name})")
                city_countries.add(c.country_id)
        for name in found.countries:
            c = by_name.get(name.lower()) or next((x for x in countries if x.iso_code.lower() == name.lower()), None)
            if c is None:
                unmatched.append(name)
                continue
            if c.id not in city_countries and all(d["country_id"] != c.id or d["city_id"] for d in dests):
                dests.append({"country_id": c.id, "city_id": None, "preference": "mandatory", "min_nights": None})
                shown.append(c.name)
        existing = {(d.country.id, d.city.id if d.city else None) for d in current.destinations}
        new = [d for d in dests if (d["country_id"], d["city_id"]) not in existing]
        if new:
            out.append(FieldSuggestion(field="destinations", label="Destinations (must visit)", value=new, merge="append",
                                       display=", ".join(s for d, s in zip(dests, shown) if d in new),
                                       evidence=evidence.get("cities") or evidence.get("countries"),
                                       current=", ".join((d.city.name if d.city else d.country.name) for d in current.destinations) or None))

        for field, label in (("interests", "Interests"), ("hotel_categories", "Hotel category"), ("food_preferences", "Food"),
                             ("meals", "Meals"), ("transport_modes", "Transport")):
            v = list(getattr(found, field))
            if v:
                cur = list(getattr(current, field))
                add(field, label, v, ", ".join(_nice(x) for x in v), merge="union", current_value=cur, current_display=", ".join(_nice(x) for x in cur))
        if found.rooms:
            v = [r.model_dump() for r in found.rooms]
            add("rooms", "Rooms", v, ", ".join(f"{r.count} × {r.type}" for r in found.rooms),
                current_value=[r.model_dump() for r in current.rooms], current_display=", ".join(f"{r.count} × {r.type}" for r in current.rooms))
        if found.travel_type:
            add("travel_type", "Travel type", found.travel_type, found.travel_type, current_value=current.travel_type, current_display=current.travel_type)
        if found.travel_pace:
            add("travel_pace", "Pace", found.travel_pace, found.travel_pace.capitalize(), current_value=current.travel_pace,
                current_display=current.travel_pace)
        currency = (found.currency or "").upper()
        for field, label in (("budget_per_person", "Budget per person"), ("budget_total", "Total budget")):
            v = getattr(found, field)
            if v:
                cur = getattr(current, field)
                add(field, label, f"{v:.2f}", f"{currency or ''} {v:,.0f}".strip(), current_value=f"{cur:.2f}" if cur is not None else None,
                    current_display=f"{current.currency} {cur:,.0f}" if cur is not None else None)
        if currency and len(currency) == 3 and (found.budget_per_person or found.budget_total):
            add("currency", "Currency", currency, currency, current_value=None if current.currency == "EUR" and not (current.budget_per_person or current.budget_total) else current.currency,
                current_display=current.currency)
        if found.special_requests:
            text_value = "\n".join(found.special_requests)
            out.append(FieldSuggestion(field="additional_requirements", label="Special requests", value=text_value, merge="append",
                                       display="; ".join(found.special_requests), current=current.additional_requirements))

        return ReadResult(provider=provider.name, provider_label=provider.label, sends_data_off_device=provider.sends_data_off_device,
                          fallback_note=note, suggestions=out, unmatched_places=list(dict.fromkeys(unmatched)),
                          special_requests=found.special_requests)
