"""Itinerary engine business tests (PRD Part 25, cases 1-10 and 15) on the demo geography."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.engines.geo import haversine_km, order_route, road_km
from app.engines.itinerary_engine import (
    AttractionInfo, CityInfo, DestinationReq, GenerationError, HotelInfo, Inventory, Requirements,
    RestaurantInfo, RoomTypeInfo, STRATEGIES, VehicleInfo, generate,
)
from app.seed import demo_inventory as demo


# ------------------------------------------------------------------ demo inventory as engine input
def build_inventory() -> Inventory:
    countries, cities, by_name = {}, {}, {}
    cid = 0
    for ci, (cname, iso, _region, rows) in enumerate(demo.COUNTRIES, start=1):
        countries[ci] = cname
        for name, lat, lng, nmin, nmax in rows:
            cid += 1
            cities[cid] = CityInfo(cid, name, ci, cname, lat, lng, nmin, nmax)
            by_name[name] = cid
    attractions = [
        AttractionInfo(i, by_name[c], n, cat, tuple(tags), dur, (), ticket, Decimal(25) if ticket else None, "EUR", False, kids, season)
        for i, (c, n, cat, tags, dur, ticket, kids, _setting, _lat, _lng, season, _d) in enumerate(demo.ATTRACTIONS, start=1)
    ]
    hotels, rt_id = [], 0
    for i, (c, n, stars, styles, loc, _fac, base) in enumerate(demo.HOTELS, start=1):
        rts = []
        for name, occ, factor in (("Double / Twin", 2, 1.0), ("Triple", 3, 1.35), ("Family room", 4, 1.6)):
            rt_id += 1
            rts.append(RoomTypeInfo(rt_id, name, occ, Decimal(round(base * factor))))
        hotels.append(HotelInfo(i, by_name[c], n, stars, tuple(styles), loc, True, None, tuple(rts), (), True))
    restaurants = [
        RestaurantInfo(i, by_name[c], n, cuisine, avg_price=Decimal(30), group_capacity=cap, **flags)
        for i, (c, n, cuisine, _pr, flags, cap) in enumerate(demo.RESTAURANTS, start=1)
    ]
    iso_to_id = {iso: i for i, (_n, iso, _r, _c) in enumerate(demo.COUNTRIES, start=1)}
    vehicles = [
        VehicleInfo(i, n, code, seats, tuple(iso_to_id[x] for x in isos), Decimal(per_day), Decimal(per_km), Decimal(driver) if driver else None)
        for i, (code, n, seats, _lug, _sup, _svc, isos, per_day, per_km, driver) in enumerate(demo.VEHICLES, start=1)
    ]
    return Inventory(cities, attractions, hotels, restaurants, vehicles, countries)


INV = build_inventory()
C = {name: i for i, name in INV.countries.items()}           # country name -> id
CITY = {c.name: c.id for c in INV.cities.values()}           # city name -> id


def req(days=15, countries=("Netherlands", "Belgium", "France", "Luxembourg", "Germany", "Switzerland"),
        pref="mandatory", **kw) -> Requirements:
    start = date(2027, 6, 1)
    base = dict(
        adults=4, children=2, children_ages=[9, 13], arrival_date=start, departure_date=start + timedelta(days=days - 1),
        arrival_airport="Amsterdam (AMS)", departure_airport="Zurich (ZRH)",
        destinations=[DestinationReq(C[c], None, pref) for c in countries],
        interests=["scenic", "lakes", "mountains", "family"], hotel_categories=["4_star"], breakfast_required=True,
        rooms=[("family", 1), ("double", 1)], food_preferences=["indian_vegetarian"], meals=["breakfast", "dinner"],
        transport_modes=["private_coach"], budget_per_person=Decimal(3000), currency="EUR",
    )
    base.update(kw)
    return Requirements(**base)


def assert_consistent(plan, r: Requirements):
    nights = (r.departure_date - r.arrival_date).days
    assert plan.total_nights == nights and plan.total_days == nights + 1
    assert sum(n for _, n in plan.stops) == nights, "nights must add up to the trip"
    assert len(plan.days) == nights + 1
    assert [d.number for d in plan.days] == list(range(1, nights + 2))
    assert [d.date for d in plan.days] == [r.arrival_date + timedelta(days=i) for i in range(nights + 1)]
    assert plan.days[-1].overnight_city_id is None and all(d.overnight_city_id for d in plan.days[:-1])
    assert sum(s.nights for s in plan.stays) == nights
    # each overnight matches the stay covering that night
    night_city = [c for c, n in plan.stops for _ in range(n)]
    assert [d.overnight_city_id for d in plan.days[:-1]] == night_city
    used = [a.attraction_id for d in plan.days for a in d.activities if a.attraction_id]
    assert len(used) == len(set(used)), "no attraction twice"


# ------------------------------------------------------------------ geo
def test_geo_estimates_are_plausible():
    ams, par = (52.3676, 4.9041), (48.8566, 2.3522)
    assert 420 < haversine_km(ams, par) < 440
    assert 520 < road_km(ams, par) < 560  # straight line × road factor, an estimate
    assert order_route([(0, 0), (0, 3), (0, 1), (0, 2)], start=0, end=1) == [0, 2, 3, 1]


# ------------------------------------------------------------------ PRD Part 25 business cases
@pytest.mark.parametrize("days", [7, 12, 15])
def test_cases_1_2_3_trip_lengths_are_consistent(days):
    r = req(days=days, countries=("Netherlands", "France", "Switzerland"), pref="preferred")
    plan = generate(r, INV, "classic")
    assert_consistent(plan, r)


def test_case_4_six_countries_all_included_in_logical_order():
    r = req()
    plan = generate(r, INV, "classic")
    assert_consistent(plan, r)
    visited = {INV.cities[c].country_id for c, _ in plan.stops}
    assert {C[x] for x in ("Netherlands", "Belgium", "France", "Luxembourg", "Germany", "Switzerland")} <= visited
    route = [INV.cities[c].name for c, _ in plan.stops]
    assert route[0] == "Amsterdam" and route[-1] == "Zurich"
    assert plan.total_distance_km < 2600, f"route has unnecessary backtracking: {route}"


def test_case_5_two_countries():
    r = req(days=10, countries=("France", "Switzerland"), arrival_airport="Paris (CDG)", departure_airport="Geneva")
    plan = generate(r, INV, "scenic")
    assert_consistent(plan, r)
    assert {INV.cities[c].country_id for c, _ in plan.stops} <= {C["France"], C["Switzerland"]}


def test_case_6_mandatory_city_never_dropped_and_min_nights_respected():
    r = req(days=8, countries=("France",), pref="preferred", arrival_airport="Paris", departure_airport="Paris",
            destinations=[DestinationReq(C["Switzerland"], CITY["Interlaken"], "mandatory", 3),
                          DestinationReq(C["France"], None, "preferred")])
    for strategy in STRATEGIES:
        plan = generate(r, INV, strategy)
        nights = dict(plan.stops)
        assert nights.get(CITY["Interlaken"], 0) >= 3


def test_mandatory_places_that_cannot_fit_are_explained_not_dropped():
    many = [DestinationReq(C[c], None, "mandatory") for c in ("Netherlands", "Belgium", "France", "Germany", "Italy", "Austria")]
    r = req(days=4, destinations=many)
    with pytest.raises(GenerationError) as e:
        generate(r, INV, "classic")
    assert "need at least" in e.value.issues[0] and "only 3" in e.value.issues[0]


def test_case_7_children_prefer_child_friendly_and_skip_unsuitable():
    unsuitable = AttractionInfo(999, CITY["Paris"], "Adults-only cabaret", "cultural", ("cultural", "scenic", "lakes", "mountains"), 120, child_friendly=False)
    inv = Inventory(INV.cities, INV.attractions + [unsuitable], INV.hotels, INV.restaurants, INV.vehicles, INV.countries)
    plan = generate(req(), inv, "classic")
    assert all(a.attraction_id != 999 for d in plan.days for a in d.activities)


def test_case_8_jain_only_verified_restaurants():
    r = req(food_preferences=["indian_jain"], meals=["breakfast", "lunch", "dinner"])
    plan = generate(r, INV, "classic")
    jain_ok = {x.id for x in INV.restaurants if x.jain is True}
    used = {m.restaurant_id for d in plan.days for m in d.meals if m.restaurant_id}
    assert used and used <= jain_ok, "only verified Jain restaurants may be suggested"
    assert any("No verified restaurant" in w for w in plan.warnings)  # cities without one are flagged
    assert any(m.arrangement == "own" and m.note for d in plan.days for m in d.meals)


def test_case_9_five_star_hotels_preferred():
    r = req(hotel_categories=["5_star"], countries=("France", "Switzerland"), arrival_airport="Paris", departure_airport="Zurich")
    plan = generate(r, INV, "classic")
    hotels = {h.id: h for h in INV.hotels}
    stays = {INV.cities[s.city_id].name: hotels[s.hotel_id].stars for s in plan.stays if s.hotel_id}
    for city, stars in stays.items():
        if city in ("Paris", "Lucerne"):
            assert stars == 5, f"{city} has a 5★ demo hotel and should use it"
    assert any("No 5★ hotel" in w for w in plan.warnings) or all(v == 5 for v in stays.values())


def test_case_10_limited_budget_is_flagged():
    r = req(budget_per_person=Decimal(300))
    plan = generate(r, INV, "classic")
    assert any("over the budget" in w for w in plan.warnings)
    assert plan.total_cost > 0 and plan.cost_per_person == (plan.total_cost / 6).quantize(Decimal("1"))


def test_case_15_three_alternatives_differ():
    r = req()
    plans = {s: generate(r, INV, s) for s in ("classic", "scenic", "premium")}
    for p in plans.values():
        assert_consistent(p, r)
    hotels = {h.id: h for h in INV.hotels}
    avg_stars = {s: sum(hotels[x.hotel_id].stars for x in p.stays if x.hotel_id) / max(1, sum(1 for x in p.stays if x.hotel_id)) for s, p in plans.items()}
    assert avg_stars["premium"] >= avg_stars["classic"]
    assert plans["premium"].total_cost >= plans["classic"].total_cost
    assert plans["scenic"].stops != plans["classic"].stops or plans["scenic"].days != plans["classic"].days


# ------------------------------------------------------------------ other rules
def test_avoided_country_never_visited():
    r = req(days=12, countries=("France", "Switzerland", "Italy"), pref="preferred", arrival_airport="Paris", departure_airport="Zurich")
    r.destinations.append(DestinationReq(C["Germany"], None, "avoid"))
    for s in STRATEGIES:
        plan = generate(r, INV, s)
        assert C["Germany"] not in {INV.cities[c].country_id for c, _ in plan.stops}


def test_costs_are_estimates_and_unknown_prices_counted():
    plan = generate(req(), INV, "classic")
    assert all(c.is_estimate for c in plan.costs)
    assert any(c.category == "hotel" and c.amount for c in plan.costs)
    assert any(c.category == "transport" and c.amount for c in plan.costs)


def test_vehicle_fits_group_and_missing_vehicle_warned():
    plan = generate(req(), INV, "classic")
    v = next(v for v in INV.vehicles if v.id == plan.vehicle_id)
    assert v.seats >= 6
    big = req(adults=60, children=0, children_ages=[], rooms=[("double", 30)])
    assert any("No vehicle" in w for w in generate(big, INV, "classic").warnings)


def test_validation_errors():
    with pytest.raises(GenerationError):
        generate(req(departure_date=date(2027, 6, 1)), INV, "classic")
