"""Deterministic itinerary generation (PRD Part 13).

Pure functions over plain dataclasses: no database, no AI. Every decision is
explainable (`explanations`) and every problem is surfaced (`warnings`).
Must-visit destinations are never silently dropped: if they cannot fit, a
`GenerationError` explains why.

Workflow: validate -> choose cities -> order route -> allocate nights ->
plan days (sightseeing, meals) -> hotels -> transport -> estimate costs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.engines.geo import drive_minutes, order_route, road_km

# ===================================================================== inputs


@dataclass(frozen=True)
class CityInfo:
    id: int
    name: str
    country_id: int
    country_name: str
    lat: float | None
    lng: float | None
    nights_min: int | None = None
    nights_max: int | None = None


@dataclass(frozen=True)
class AttractionInfo:
    id: int
    city_id: int
    name: str
    category: str
    interest_tags: tuple[str, ...] = ()
    duration_min: int | None = None
    operating_days: tuple[str, ...] = ()
    ticket_required: bool = False
    ticket_price: Decimal | None = None
    currency: str = "EUR"
    price_verified: bool = False
    child_friendly: bool | None = None
    seasonal_info: str | None = None


@dataclass(frozen=True)
class RoomTypeInfo:
    id: int
    name: str
    max_occupancy: int
    base_price: Decimal | None
    currency: str = "EUR"
    price_verified: bool = False


@dataclass(frozen=True)
class RateInfo:
    room_type_id: int
    valid_from: date
    valid_to: date
    price: Decimal
    currency: str = "EUR"
    verified: bool = False


@dataclass(frozen=True)
class HotelInfo:
    id: int
    city_id: int
    name: str
    stars: int | None
    styles: tuple[str, ...] = ()
    location_type: str | None = None
    breakfast: bool | None = None
    group_capacity_rooms: int | None = None
    room_types: tuple[RoomTypeInfo, ...] = ()
    rates: tuple[RateInfo, ...] = ()
    is_demo: bool = False


@dataclass(frozen=True)
class RestaurantInfo:
    id: int
    city_id: int
    name: str
    cuisine: str | None = None
    vegetarian: bool | None = None
    jain: bool | None = None
    halal: bool | None = None
    vegan: bool | None = None
    non_vegetarian: bool | None = None
    avg_price: Decimal | None = None
    currency: str = "EUR"
    price_verified: bool = False
    group_capacity: int | None = None


@dataclass(frozen=True)
class VehicleInfo:
    id: int
    name: str
    category_code: str
    seats: int
    country_ids: tuple[int, ...] = ()
    price_per_day: Decimal | None = None
    price_per_km: Decimal | None = None
    driver_cost_per_day: Decimal | None = None
    currency: str = "EUR"
    price_verified: bool = False


@dataclass
class Inventory:
    cities: dict[int, CityInfo]
    attractions: list[AttractionInfo] = field(default_factory=list)
    hotels: list[HotelInfo] = field(default_factory=list)
    restaurants: list[RestaurantInfo] = field(default_factory=list)
    vehicles: list[VehicleInfo] = field(default_factory=list)
    countries: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DestinationReq:
    country_id: int
    city_id: int | None
    preference: str  # mandatory / preferred / optional / avoid
    min_nights: int | None = None


@dataclass
class Requirements:
    adults: int
    children: int
    children_ages: list[int]
    arrival_date: date | None
    departure_date: date | None
    arrival_airport: str | None = None
    departure_airport: str | None = None
    start_country_id: int | None = None
    end_country_id: int | None = None
    destinations: list[DestinationReq] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    travel_pace: str | None = None
    hotel_categories: list[str] = field(default_factory=list)
    hotel_locations: list[str] = field(default_factory=list)
    breakfast_required: bool = True
    rooms: list[tuple[str, int]] = field(default_factory=list)
    food_preferences: list[str] = field(default_factory=list)
    meals: list[str] = field(default_factory=lambda: ["breakfast"])
    transport_modes: list[str] = field(default_factory=list)
    passenger_capacity: int | None = None
    airport_transfers: bool = True
    budget_per_person: Decimal | None = None
    budget_total: Decimal | None = None
    currency: str = "EUR"

    @property
    def travellers(self) -> int:
        return self.adults + self.children


# ===================================================================== outputs


@dataclass
class PlannedActivity:
    time_slot: str  # morning / afternoon / evening / full_day
    kind: str  # arrival, transfer, check_in, check_out, sightseeing, free_time, departure
    title: str
    description: str | None = None
    attraction_id: int | None = None
    duration_min: int | None = None


@dataclass
class PlannedMeal:
    meal: str  # breakfast / lunch / dinner
    arrangement: str  # hotel / restaurant / own
    restaurant_id: int | None = None
    note: str | None = None


@dataclass
class PlannedDay:
    number: int
    date: date
    city_id: int
    title: str
    overnight_city_id: int | None
    activities: list[PlannedActivity] = field(default_factory=list)
    meals: list[PlannedMeal] = field(default_factory=list)


@dataclass
class PlannedStay:
    city_id: int
    check_in_day: int
    nights: int
    hotel_id: int | None
    rooms: list[tuple[int | None, str, int, Decimal | None]]  # (room_type_id, label, count, price/night)
    alternatives: list[int] = field(default_factory=list)
    estimated_cost: Decimal | None = None
    note: str | None = None


@dataclass
class PlannedLeg:
    day_number: int
    from_city_id: int | None
    to_city_id: int | None
    kind: str  # airport_transfer / intercity
    mode: str  # coach / car / minibus / train
    vehicle_id: int | None
    distance_km: int | None
    duration_min: int | None
    is_estimate: bool = True
    note: str | None = None


@dataclass
class CostLine:
    category: str  # hotel / transport / sightseeing / meals
    description: str
    amount: Decimal | None  # None = unknown (no price in inventory)
    currency: str
    is_estimate: bool = True


@dataclass
class Plan:
    strategy: str
    title: str
    total_days: int
    total_nights: int
    stops: list[tuple[int, int]]  # (city_id, nights) in route order
    days: list[PlannedDay]
    stays: list[PlannedStay]
    legs: list[PlannedLeg]
    vehicle_id: int | None
    costs: list[CostLine]
    total_cost: Decimal
    cost_per_person: Decimal
    currency: str
    unknown_cost_items: int
    total_distance_km: int
    explanations: list[str]
    warnings: list[str]


class GenerationError(Exception):
    """Requirements cannot produce a valid itinerary; `issues` explains why."""

    def __init__(self, issues: list[str]):
        super().__init__("; ".join(issues))
        self.issues = issues


# ===================================================================== strategies

STRATEGIES: dict[str, dict] = {
    "classic": {
        "title": "Classic Europe",
        "summary": "Major destinations and popular sightseeing at a balanced pace.",
        "boost": {"landmark": 2.0, "museum": 2.0, "cultural": 1.5, "tour": 1.0, "shopping": 0.5},
        "tags": {"historical_landmarks": 1.5, "museums": 1.5, "cultural": 1.0, "shopping": 0.5},
        "pace": "balanced",
        "star_shift": 0,
        "styles": (),
        "luxury_vehicle": False,
    },
    "scenic": {
        "title": "Scenic Europe",
        "summary": "Mountains, lakes and nature with a relaxed pace.",
        "boost": {"mountain": 3.0, "lake": 3.0, "nature": 2.5, "scenic": 2.5, "tour": 0.5},
        "tags": {"mountains": 2.0, "lakes": 2.0, "nature": 1.5, "scenic": 1.5, "photography": 0.5},
        "pace": "relaxed",
        "star_shift": 0,
        "styles": ("resort", "family"),
        "luxury_vehicle": False,
    },
    "premium": {
        "title": "Premium Europe",
        "summary": "Higher-category hotels, premium transport and enhanced sightseeing.",
        "boost": {"landmark": 2.0, "museum": 1.5, "mountain": 1.5, "lake": 1.5, "tour": 1.5, "cultural": 1.0},
        "tags": {"historical_landmarks": 1.0, "museums": 1.0, "mountains": 1.0, "scenic": 1.0},
        "pace": "balanced",
        "star_shift": 1,
        "styles": ("luxury", "boutique"),
        "luxury_vehicle": True,
    },
}
PACE = {  # minimum nights per stop, target nights per stop (sets how many stops fit)
    "relaxed": (2, 3.0),
    "balanced": (1, 2.4),
    "fast": (1, 1.8),
}
ROOM_SLEEPS = {"single": 1, "double": 2, "twin": 2, "triple": 3, "family": 4, "suite": 2}
DIET_FLAGS = {"indian_vegetarian": "vegetarian", "indian_jain": "jain", "halal": "halal", "vegan": "vegan"}
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SLOT_MINUTES = 210  # a morning or afternoon block


# ===================================================================== entry point


def generate(req: Requirements, inv: Inventory, strategy: str) -> Plan:
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy {strategy}")
    cfg = STRATEGIES[strategy]
    _validate(req)
    nights = (req.departure_date - req.arrival_date).days
    ctx = _Context(req, inv, cfg, strategy)

    stops = ctx.choose_cities(nights)
    stops = ctx.order(stops)
    allocation = ctx.allocate_nights(stops, nights)
    days, used_attractions = ctx.plan_days(allocation)
    stays = ctx.plan_hotels(allocation)
    vehicle = ctx.choose_vehicle(allocation)
    legs = ctx.plan_legs(allocation, vehicle)
    ctx.plan_meals(days, allocation)
    costs = ctx.estimate_costs(stays, legs, vehicle, days, used_attractions, nights)

    known = [c.amount for c in costs if c.amount is not None and c.currency == req.currency]
    total = sum(known, Decimal(0)).quantize(Decimal("1"))
    per_person = (total / req.travellers).quantize(Decimal("1")) if req.travellers else Decimal(0)
    unknown = sum(1 for c in costs if c.amount is None)
    ctx.compare_budget(total, unknown)
    distance = sum(l.distance_km or 0 for l in legs if l.kind == "intercity")
    ctx.explanations.append(
        f"Route: {' → '.join(inv.cities[c].name for c, _ in allocation)} · about {distance:,} km by road (estimate)."
    )
    return Plan(
        strategy=strategy, title=cfg["title"], total_days=nights + 1, total_nights=nights,
        stops=allocation, days=days, stays=stays, legs=legs, vehicle_id=vehicle.id if vehicle else None,
        costs=costs, total_cost=total, cost_per_person=per_person, currency=req.currency,
        unknown_cost_items=unknown, total_distance_km=distance,
        explanations=ctx.explanations, warnings=ctx.warnings,
    )


def _validate(req: Requirements) -> None:
    issues = []
    if not req.arrival_date or not req.departure_date:
        issues.append("Arrival and departure dates are required.")
    elif req.departure_date <= req.arrival_date:
        issues.append("The trip needs at least one night (departure must be after arrival).")
    if req.travellers < 1:
        issues.append("At least one traveller is required.")
    if not any(d.preference != "avoid" for d in req.destinations) and not req.arrival_airport:
        issues.append("Add at least one destination to visit.")
    if issues:
        raise GenerationError(issues)


# ===================================================================== implementation


class _Context:
    def __init__(self, req: Requirements, inv: Inventory, cfg: dict, strategy: str):
        self.req, self.inv, self.cfg, self.strategy = req, inv, cfg, strategy
        self.explanations: list[str] = []
        self.warnings: list[str] = []
        self.pace = req.travel_pace or cfg["pace"]
        self.avoid_countries = {d.country_id for d in req.destinations if d.preference == "avoid" and d.city_id is None}
        self.avoid_cities = {d.city_id for d in req.destinations if d.preference == "avoid" and d.city_id}
        self.attractions_by_city: dict[int, list[AttractionInfo]] = {}
        for a in inv.attractions:
            self.attractions_by_city.setdefault(a.city_id, []).append(a)

    # ------------------------------------------------------------- scoring
    def attraction_score(self, a: AttractionInfo) -> float:
        score = (1.0 + 2.0 * len(set(a.interest_tags) & set(self.req.interests))
                 + self.cfg["boost"].get(a.category, 0.0)
                 + sum(self.cfg["tags"].get(t, 0.0) for t in a.interest_tags))
        if self.req.children:
            if a.child_friendly is False:
                return -1.0  # never schedule attractions marked unsuitable for children on a family trip
            if a.child_friendly is True:
                score += 1.0
        return score

    def city_score(self, city_id: int) -> float:
        attractions = self.attractions_by_city.get(city_id, [])
        return 0.5 + sum(max(self.attraction_score(a), 0) for a in attractions)

    def selection_score(self, city_id: int) -> float:
        """City attractiveness for this strategy, strongly preferring cities where we have a hotel."""
        has_hotel = any(h.city_id == city_id for h in self.inv.hotels)
        return self.city_score(city_id) + (4.0 if has_hotel else -4.0)

    def best_city_in(self, country_id: int, exclude: set[int]) -> CityInfo | None:
        options = [c for c in self.inv.cities.values() if c.country_id == country_id and c.id not in exclude and c.id not in self.avoid_cities]
        return max(options, key=lambda c: (self.selection_score(c.id), -c.id), default=None)

    def match_airport_city(self, text: str | None, country_id: int | None) -> CityInfo | None:
        if text:
            t = text.lower()
            hits = [c for c in self.inv.cities.values() if c.name.lower() in t]
            if hits:
                return max(hits, key=lambda c: len(c.name))
        if country_id:
            return self.best_city_in(country_id, set())
        return None

    # ------------------------------------------------------------- 2: choose cities
    def choose_cities(self, nights: int) -> list[dict]:
        req, cities = self.req, self.inv.cities
        min_n, target = PACE.get(self.pace, PACE["balanced"])
        chosen: list[dict] = []

        def add(city: CityInfo, reason: str, must: bool, min_nights: int | None = None):
            for s in chosen:
                if s["city"].id == city.id:
                    s["must"] = s["must"] or must
                    s["min"] = max(s["min"] or 0, min_nights or 0) or None
                    s["reasons"].append(reason)
                    return
            chosen.append({"city": city, "reasons": [reason], "must": must, "min": min_nights, "role": None})

        start = self.match_airport_city(req.arrival_airport, req.start_country_id)
        end = self.match_airport_city(req.departure_airport, req.end_country_id)
        for role, city in (("start", start), ("end", end)):
            if city is None:
                continue
            if city.country_id in self.avoid_countries or city.id in self.avoid_cities:
                self.warnings.append(f"{city.name} is where the trip {'starts' if role == 'start' else 'ends'} but is marked to avoid; kept for the {'arrival' if role == 'start' else 'departure'} only.")
            add(city, "arrival point" if role == "start" else "departure point", True)
        for s in chosen:
            if start and s["city"].id == start.id:
                s["role"] = "start"
        if end and start and end.id != start.id:
            for s in chosen:
                if s["city"].id == end.id:
                    s["role"] = "end"

        def covered(country_id):
            # Arrival/departure cities are logistics, not a choice: they don't count as visiting the country,
            # so e.g. a scenic trip ending in Zurich still adds the best scenic Swiss city.
            return any(s["city"].country_id == country_id and (s["role"] is None or len(s["reasons"]) > 1) for s in chosen)

        # must-visit destinations (never dropped)
        for d in req.destinations:
            if d.preference != "mandatory":
                continue
            if d.city_id:
                city = cities.get(d.city_id)
                if city is None:
                    raise GenerationError([f"A must-visit city (id {d.city_id}) is not in the active inventory."])
                add(city, "must-visit", True, d.min_nights)
            elif not covered(d.country_id):
                city = self.best_city_in(d.country_id, set())
                if city is None:
                    raise GenerationError([f"Must-visit country {self.inv.countries.get(d.country_id, d.country_id)} has no active cities in inventory."])
                add(city, f"must-visit country {city.country_name}", True, d.min_nights)
            else:
                if d.min_nights:
                    for s in chosen:
                        if s["city"].country_id == d.country_id:
                            s["min"] = max(s["min"] or 0, d.min_nights)
                            break
        must = [s for s in chosen if s["must"]]
        if len(must) > nights:
            raise GenerationError([
                f"{len(must)} must-visit places (incl. arrival/departure cities) need at least {len(must)} nights, but the trip has only {nights}. "
                "Extend the trip or change some must-visits to preferred."
            ])
        max_stops = max(len(must), min(nights, max(1, math.floor(nights / target + 0.25))))

        # preferred, then optional: ranked by how well they match this strategy
        for pref in ("preferred", "optional"):
            candidates: list[tuple[float, CityInfo, int | None]] = []
            for d in req.destinations:
                if d.preference != pref:
                    continue
                if d.city_id:
                    c = cities.get(d.city_id)
                    if c and c.id not in self.avoid_cities:
                        candidates.append((self.city_score(c.id) + 5, c, d.min_nights))
                elif d.country_id not in self.avoid_countries and not covered(d.country_id):
                    c = self.best_city_in(d.country_id, {s["city"].id for s in chosen})
                    if c:
                        candidates.append((self.city_score(c.id), c, d.min_nights))
            for score, c, mn in sorted(candidates, key=lambda x: (-x[0], x[1].id)):
                if len(chosen) >= max_stops:
                    self.explanations.append(f"{c.name} ({pref}) left out: not enough nights at a {self.pace} pace.")
                    continue
                if pref == "preferred" or score > 2:
                    add(c, pref, False, mn)
        # extra city in a wanted country if nights allow (e.g. a second Swiss stop on a scenic trip)
        wanted = {d.country_id for d in req.destinations if d.preference != "avoid"}
        while len(chosen) < max_stops:
            extra = [c for c in cities.values() if c.country_id in wanted and c.id not in {s["city"].id for s in chosen}
                     and c.id not in self.avoid_cities and self.city_score(c.id) >= 6]
            if not extra:
                break
            best = max(extra, key=lambda c: (self.city_score(c.id), -c.id))
            add(best, f"adds {', '.join(self._top_categories(best.id))} to the trip", False)

        for s in chosen:
            self.explanations.append(f"{s['city'].name}: {', '.join(dict.fromkeys(s['reasons']))}.")
        if len(must) and len(must) * min_n > nights:
            self.warnings.append(f"Must-visit places get fewer than {min_n} nights each at a {self.pace} pace; the schedule will be tight.")
        return chosen

    def _top_categories(self, city_id: int) -> list[str]:
        cats = sorted({a.category for a in self.attractions_by_city.get(city_id, [])}, key=lambda c: -self.cfg["boost"].get(c, 0))
        return [c.replace("_", " ") for c in cats[:2]] or ["variety"]

    # ------------------------------------------------------------- 4: route
    def order(self, stops: list[dict]) -> list[dict]:
        if len(stops) <= 1:
            return stops
        placeable = [s for s in stops if s["city"].lat is not None and s["city"].lng is not None]
        missing = [s for s in stops if s not in placeable]
        for s in missing:
            self.warnings.append(f"{s['city'].name} has no coordinates; it was placed at the end of the route. Add coordinates for a better route.")
        points = [(s["city"].lat, s["city"].lng) for s in placeable]
        start = next((i for i, s in enumerate(placeable) if s["role"] == "start"), None)
        end = next((i for i, s in enumerate(placeable) if s["role"] == "end"), None)
        order = order_route(points, start, end)
        return [placeable[i] for i in order] + missing

    # ------------------------------------------------------------- 5: nights
    def allocate_nights(self, stops: list[dict], nights: int) -> list[tuple[int, int]]:
        min_n, _ = PACE.get(self.pace, PACE["balanced"])
        alloc = []
        for s in stops:
            c = s["city"]
            base = max(1, s["min"] or 0, min(min_n, c.nights_min or min_n))
            alloc.append(base)
        # too many nights requested: shrink non-must first, then must-visits towards 1
        while sum(alloc) > nights:
            shrinkable = [i for i, n in enumerate(alloc) if n > 1]
            if not shrinkable:
                break
            i = max(shrinkable, key=lambda i: (not stops[i]["must"], alloc[i], -i))
            alloc[i] -= 1
        while sum(alloc) > nights:  # still too many stops: drop lowest-value non-must stop
            droppable = [i for i, s in enumerate(stops) if not s["must"]]
            if not droppable:
                raise GenerationError([f"The must-visit places cannot fit into {nights} nights."])
            i = min(droppable, key=lambda i: (self.city_score(stops[i]["city"].id), -i))
            self.explanations.append(f"{stops[i]['city'].name} left out: not enough nights.")
            del stops[i], alloc[i]
        if any(s["min"] and n < s["min"] for s, n in zip(stops, alloc)):
            self.warnings.append("Some minimum-night requests could not be met within the trip length.")
        # distribute remaining nights to where the most matching sightseeing is
        content = [self._content_minutes(s["city"].id) for s in stops]
        affinity = [self._affinity(s["city"].id) for s in stops]
        while sum(alloc) < nights:
            def headroom(i):
                cap = stops[i]["city"].nights_max or 4
                return alloc[i] < max(cap, 1)

            def unseen(i):  # sightseeing minutes not yet covered by the nights already given
                capacity = 150 + (alloc[i] - 1) * SLOT_MINUTES * 2
                return content[i] - capacity

            pool = [i for i in range(len(stops)) if headroom(i)] or list(range(len(stops)))
            i = max(pool, key=lambda i: (unseen(i) + 45 * affinity[i] / alloc[i], self.city_score(stops[i]["city"].id) / (alloc[i] + 0.5), -i))
            alloc[i] += 1
        return [(s["city"].id, n) for s, n in zip(stops, alloc)]

    def _affinity(self, city_id: int) -> float:
        """How strongly a city's sightseeing matches this strategy's character (0 = not at all)."""
        return sum(self.cfg["boost"].get(a.category, 0.0) + sum(self.cfg["tags"].get(t, 0.0) for t in a.interest_tags)
                   for a in self.attractions_by_city.get(city_id, []) if self.attraction_score(a) > 0)

    def _content_minutes(self, city_id: int) -> int:
        return sum(a.duration_min or 120 for a in self.attractions_by_city.get(city_id, []) if self.attraction_score(a) > 0)

    # ------------------------------------------------------------- 6: days & sightseeing
    def plan_days(self, alloc: list[tuple[int, int]]):
        req, cities = self.req, self.inv.cities
        days: list[PlannedDay] = []
        used: set[int] = set()
        day = 1
        for k, (city_id, n) in enumerate(alloc):
            city = cities[city_id]
            for offset in range(n):
                d = req.arrival_date + timedelta(days=day - 1)
                pd = PlannedDay(number=day, date=d, city_id=city_id, title=city.name, overnight_city_id=city_id)
                if offset == 0 and k == 0:
                    pd.title = f"Arrival in {city.name}"
                    pd.activities.append(PlannedActivity("morning", "arrival", f"Arrive at {req.arrival_airport or city.name}",
                                                         "Meet and greet; private transfer to the hotel." if req.airport_transfers else None))
                    pd.activities.append(PlannedActivity("afternoon", "check_in", f"Hotel check-in in {city.name}"))
                    self._sightsee(pd, city_id, used, ["evening"], max_minutes=150, light=True)
                elif offset == 0:
                    prev = cities[alloc[k - 1][0]]
                    km = road_km((prev.lat, prev.lng), (city.lat, city.lng)) if None not in (prev.lat, prev.lng, city.lat, city.lng) else None
                    minutes = drive_minutes(km) if km else None
                    pd.title = f"{prev.name} → {city.name}"
                    pd.activities.append(PlannedActivity("morning", "check_out", f"Check out in {prev.name}"))
                    pd.activities.append(PlannedActivity(
                        "morning", "transfer", f"Travel to {city.name}",
                        f"About {km:,} km, ~{minutes // 60} h {minutes % 60:02d} min (estimate)." if km else "Travel time to be confirmed.",
                        duration_min=minutes))
                    pd.activities.append(PlannedActivity("afternoon", "check_in", f"Hotel check-in in {city.name}"))
                    if minutes is None or minutes <= 240:
                        self._sightsee(pd, city_id, used, ["afternoon"], max_minutes=150)
                else:
                    pd.title = f"{city.name} sightseeing"
                    self._sightsee(pd, city_id, used, ["morning", "afternoon"], max_minutes=SLOT_MINUTES * 2)
                    if not any(a.kind == "sightseeing" for a in pd.activities):
                        pd.title = f"{city.name}: leisure day"
                        pd.activities.append(PlannedActivity("full_day", "free_time", "Free day", "At leisure, or add an optional excursion."))
                if pd.number != 1 or not any(a.kind == "sightseeing" for a in pd.activities):
                    pd.activities.append(PlannedActivity("evening", "free_time", "Evening at leisure"))
                days.append(pd)
                day += 1
        last = cities[alloc[-1][0]]
        dep = PlannedDay(number=day, date=req.arrival_date + timedelta(days=day - 1), city_id=last.id,
                         title=f"Departure from {req.departure_airport or last.name}", overnight_city_id=None)
        dep.activities.append(PlannedActivity("morning", "check_out", f"Check out in {last.name}"))
        dep.activities.append(PlannedActivity("morning", "departure", f"Transfer to {req.departure_airport or last.name}" if req.airport_transfers else "Departure",
                                              "End of services."))
        days.append(dep)
        return days, used

    def _sightsee(self, pd: PlannedDay, city_id: int, used: set[int], slots: list[str], max_minutes: int, light: bool = False):
        weekday = WEEKDAYS[pd.date.weekday()]
        options = [a for a in self.attractions_by_city.get(city_id, []) if a.id not in used and self.attraction_score(a) > 0]
        options.sort(key=lambda a: (-self.attraction_score(a), a.id))
        remaining = max_minutes
        for a in options:
            if a.operating_days and weekday not in a.operating_days:
                continue
            duration = a.duration_min or 120
            if light and duration > 150:
                continue
            if duration > remaining and not (duration > SLOT_MINUTES and remaining == max_minutes and max_minutes >= SLOT_MINUTES * 2):
                continue
            slot = "full_day" if duration > SLOT_MINUTES else (slots[0] if remaining == max_minutes else slots[-1])
            note = a.seasonal_info and f"Seasonal: {a.seasonal_info}"
            pd.activities.append(PlannedActivity(slot, "sightseeing", a.name, note, attraction_id=a.id, duration_min=duration))
            used.add(a.id)
            remaining -= duration
            if remaining < 60:
                break

    # ------------------------------------------------------------- 7: meals
    def plan_meals(self, days: list[PlannedDay], alloc: list[tuple[int, int]]) -> None:
        req = self.req
        flags = {DIET_FLAGS[f] for f in req.food_preferences if f in DIET_FLAGS}
        indian = any(f.startswith("indian") for f in req.food_preferences)
        usage: dict[int, int] = {}
        missing_cities: set[str] = set()
        for pd in days:
            city = self.inv.cities[pd.city_id]
            if "breakfast" in req.meals and pd.number > 1:
                pd.meals.append(PlannedMeal("breakfast", "hotel" if req.breakfast_required else "own"))
            for meal in ("lunch", "dinner"):
                if meal not in req.meals or (pd.overnight_city_id is None and meal == "dinner"):
                    continue
                r = self._restaurant(pd.city_id, flags, indian, usage)
                if r:
                    usage[r.id] = usage.get(r.id, 0) + 1
                    pd.meals.append(PlannedMeal(meal, "restaurant", r.id))
                else:
                    pd.meals.append(PlannedMeal(meal, "own", None, "No restaurant with the required verified dietary option in inventory; to be arranged."))
                    missing_cities.add(city.name)
        if missing_cities and req.meals != ["breakfast"]:
            need = ", ".join(sorted(f.replace("_", " ") for f in req.food_preferences)) or "the requested meals"
            self.warnings.append(f"No verified restaurant for {need} in: {', '.join(sorted(missing_cities))}. Those meals are marked 'to be arranged'.")

    def _restaurant(self, city_id: int, flags: set[str], indian: bool, usage: dict[int, int]) -> RestaurantInfo | None:
        options = [r for r in self.inv.restaurants if r.city_id == city_id and all(getattr(r, f) is True for f in flags)
                   and (r.group_capacity is None or r.group_capacity >= self.req.travellers)]
        if not options:
            return None
        # Indian food preferences: an Indian restaurant with the verified option comes first; rotate within that group.
        return min(options, key=lambda r: (not (indian and r.cuisine and "indian" in r.cuisine.lower()), usage.get(r.id, 0), r.id))

    # ------------------------------------------------------------- 6b: hotels
    def wanted_stars(self) -> set[int]:
        stars = {int(c[0]) for c in self.req.hotel_categories if c.endswith("_star")}
        if not stars:
            stars = {5} if "luxury" in self.req.hotel_categories else {3} if "budget" in self.req.hotel_categories else {4}
        return {min(5, s + self.cfg["star_shift"]) for s in stars}

    def room_needs(self) -> list[tuple[str, int]]:
        if self.req.rooms:
            return self.req.rooms
        return [("double", max(1, math.ceil(self.req.travellers / 2)))]

    def plan_hotels(self, alloc: list[tuple[int, int]]) -> list[PlannedStay]:
        stars = self.wanted_stars()
        styles = set(self.req.hotel_categories) | set(self.cfg["styles"])
        needs = self.room_needs()
        total_rooms = sum(c for _, c in needs)
        stays, day = [], 1
        for city_id, n in alloc:
            check_in = self.req.arrival_date + timedelta(days=day - 1)
            candidates = []
            for h in self.inv.hotels:
                if h.city_id != city_id:
                    continue
                score = 0.0
                if h.stars in stars:
                    score += 10
                elif h.stars is not None and min(abs(h.stars - s) for s in stars) == 1:
                    score += 4
                score += 3 * len(styles & set(h.styles))
                if h.location_type and h.location_type in self.req.hotel_locations:
                    score += 2
                if self.req.breakfast_required:
                    score += {True: 2, None: 0, False: -6}[h.breakfast]
                if h.group_capacity_rooms is not None and h.group_capacity_rooms < total_rooms:
                    score -= 8
                rooms, price = self._assign_rooms(h, needs, check_in)
                if any(rt is None for rt, *_ in rooms):
                    score -= 3
                candidates.append((score, price, h, rooms))
            if not candidates:
                self.warnings.append(f"No hotel in inventory for {self.inv.cities[city_id].name}; add one or arrange separately.")
                stays.append(PlannedStay(city_id, day, n, None, [], note="No hotel in inventory"))
            else:
                premium = self.cfg["star_shift"] > 0
                candidates.sort(key=lambda c: (-c[0], (-(c[1] or 0)) if premium else (c[1] if c[1] is not None else Decimal(10**9)), c[2].id))
                score, price, h, rooms = candidates[0]
                if h.stars not in stars:
                    self.warnings.append(f"No {'/'.join(f'{s}★' for s in sorted(stars))} hotel in {self.inv.cities[city_id].name}; suggested {h.name} ({h.stars or '?'}★).")
                cost = price * n if price is not None else None
                stays.append(PlannedStay(city_id, day, n, h.id, rooms, [c[2].id for c in candidates[1:3]], cost,
                                         "Availability not verified"))
            day += n
        return stays

    def _assign_rooms(self, h: HotelInfo, needs: list[tuple[str, int]], on: date):
        rooms, total = [], Decimal(0)
        unknown = False
        for kind, count in needs:
            sleeps = ROOM_SLEEPS.get(kind, 2)
            by_name = [rt for rt in h.room_types if kind in rt.name.lower()]
            fitting = by_name or sorted([rt for rt in h.room_types if rt.max_occupancy >= sleeps], key=lambda rt: rt.max_occupancy)
            rt = fitting[0] if fitting else None
            price = self._room_price(h, rt, on) if rt else None
            rooms.append((rt.id if rt else None, rt.name if rt else f"{kind} room", count, price))
            if price is None:
                unknown = True
            else:
                total += price * count
        return rooms, (None if unknown else total)

    @staticmethod
    def _room_price(h: HotelInfo, rt: RoomTypeInfo, on: date) -> Decimal | None:
        for r in h.rates:
            if r.room_type_id == rt.id and r.valid_from <= on <= r.valid_to:
                return r.price
        return rt.base_price

    # ------------------------------------------------------------- 8: transport
    def choose_vehicle(self, alloc: list[tuple[int, int]]) -> VehicleInfo | None:
        req = self.req
        seats = req.passenger_capacity or req.travellers
        modes = set(req.transport_modes)
        countries = {self.inv.cities[c].country_id for c, _ in alloc}
        pool = [v for v in self.inv.vehicles if v.seats >= seats]
        if "private_car" in modes and seats <= 8:
            pool = [v for v in pool if v.seats <= 8] or pool
        if not pool:
            self.warnings.append(f"No vehicle in inventory with at least {seats} seats.")
            return None
        luxury = "luxury_coach" in modes or self.cfg["luxury_vehicle"]

        def key(v: VehicleInfo):
            coverage = len(countries & set(v.country_ids)) if v.country_ids else 0
            is_lux = v.category_code == "luxury_coach"
            return (-coverage, 0 if (is_lux == luxury) else 1, v.seats, v.id)

        v = min(pool, key=key)
        uncovered = countries - set(v.country_ids) if v.country_ids else set()
        if uncovered:
            names = ", ".join(sorted(self.inv.countries.get(c, str(c)) for c in uncovered))
            self.warnings.append(f"{v.name} is not listed as operating in: {names}. Confirm with the supplier or split the transport.")
        self.explanations.append(f"Transport: {v.name} ({v.seats} seats) for {seats} passengers.")
        return v

    def plan_legs(self, alloc: list[tuple[int, int]], vehicle: VehicleInfo | None) -> list[PlannedLeg]:
        req, cities = self.req, self.inv.cities
        train = "train" in req.transport_modes
        mode = "car" if vehicle and vehicle.seats <= 8 else "minibus" if vehicle and vehicle.seats <= 25 else "coach"
        legs, day = [], 1
        if req.airport_transfers:
            legs.append(PlannedLeg(1, None, alloc[0][0], "airport_transfer", mode, vehicle.id if vehicle else None, None, None,
                                   note=f"From {req.arrival_airport or 'arrival point'}"))
        for k, (city_id, n) in enumerate(alloc):
            if k > 0:
                prev = cities[alloc[k - 1][0]]
                cur = cities[city_id]
                km = road_km((prev.lat, prev.lng), (cur.lat, cur.lng)) if None not in (prev.lat, prev.lng, cur.lat, cur.lng) else None
                leg_mode = "train" if train and km and km > 250 else mode
                legs.append(PlannedLeg(day, prev.id, cur.id, "intercity", leg_mode, None if leg_mode == "train" else (vehicle.id if vehicle else None),
                                       km, drive_minutes(km) if km else None,
                                       note="Train suggested for this longer leg (fare not in inventory)." if leg_mode == "train" else None))
            day += n
        if req.airport_transfers:
            legs.append(PlannedLeg(day, alloc[-1][0], None, "airport_transfer", mode, vehicle.id if vehicle else None, None, None,
                                   note=f"To {req.departure_airport or 'departure point'}"))
        long_legs = [l for l in legs if l.duration_min and l.duration_min > 6 * 60 and l.mode != "train"]
        for l in long_legs:
            self.warnings.append(f"Long travel day {l.day_number}: {cities[l.from_city_id].name} → {cities[l.to_city_id].name} ≈ {l.duration_min // 60} h by road (estimate).")
        return legs

    # ------------------------------------------------------------- 9: costs
    def estimate_costs(self, stays, legs, vehicle, days, used_attractions, nights) -> list[CostLine]:
        req, cur = self.req, self.req.currency
        lines: list[CostLine] = []
        for s in stays:
            city = self.inv.cities[s.city_id].name
            hotel = next((h for h in self.inv.hotels if h.id == s.hotel_id), None)
            label = f"{hotel.name if hotel else 'Hotel'}, {city}, {s.nights} night{'s' if s.nights != 1 else ''}"
            lines.append(CostLine("hotel", label, s.estimated_cost.quantize(Decimal('1')) if s.estimated_cost is not None else None, cur))
        if vehicle:
            used_days = nights + 1
            if vehicle.price_per_day is not None:
                amount = (vehicle.price_per_day + (vehicle.driver_cost_per_day or 0)) * used_days
            elif vehicle.price_per_km is not None:
                amount = vehicle.price_per_km * sum(l.distance_km or 0 for l in legs)
            else:
                amount = None
            lines.append(CostLine("transport", f"{vehicle.name}, {used_days} days incl. driver", amount, vehicle.currency))
        for l in legs:
            if l.mode == "train":
                lines.append(CostLine("transport", f"Train {self.inv.cities[l.from_city_id].name} → {self.inv.cities[l.to_city_id].name}", None, cur))
        by_id = {a.id: a for a in self.inv.attractions}
        for aid in sorted(used_attractions):
            a = by_id[aid]
            if a.ticket_required:
                amount = a.ticket_price * req.travellers if a.ticket_price is not None else None
                lines.append(CostLine("sightseeing", f"{a.name} tickets × {req.travellers}", amount, a.currency))
        rest_by_id = {r.id: r for r in self.inv.restaurants}
        meal_count: dict[int, int] = {}
        for pd in days:
            for m in pd.meals:
                if m.restaurant_id:
                    meal_count[m.restaurant_id] = meal_count.get(m.restaurant_id, 0) + 1
        for rid, count in sorted(meal_count.items()):
            r = rest_by_id[rid]
            amount = r.avg_price * req.travellers * count if r.avg_price is not None else None
            lines.append(CostLine("meals", f"{r.name}: {count} meal{'s' if count != 1 else ''} × {req.travellers}", amount, r.currency))
        other_currency = [l for l in lines if l.amount is not None and l.currency != cur]
        if other_currency:
            self.warnings.append(f"{len(other_currency)} cost item(s) are priced in another currency and are excluded from the {cur} total.")
        return lines

    def compare_budget(self, total: Decimal, unknown: int) -> None:
        req = self.req
        budget = req.budget_total or (req.budget_per_person * req.travellers if req.budget_per_person is not None else None)
        if unknown:
            self.warnings.append(f"{unknown} cost item(s) have no price in inventory: the estimate is incomplete.")
        if budget and total > budget:
            over = (total - budget) / budget * 100
            self.warnings.append(f"Estimated cost {total:,.0f} {req.currency} is {over:.0f}% over the budget of {budget:,.0f} {req.currency}.")
        elif budget:
            self.explanations.append(f"Estimated cost {total:,.0f} {req.currency} is within the budget of {budget:,.0f} {req.currency} (estimate).")
