import uuid

import pytest

from tests.conftest import unique_iso

API = "/api/v1"


def _uid():
    return uuid.uuid4().hex[:6]


@pytest.fixture()
def world(admin_client):
    """Netherlands / France / Switzerland-like world with real coordinates (names unique per test)."""
    c = admin_client
    tag = _uid()

    def country(name):
        return c.post(f"{API}/inventory/countries", json={"name": f"{name} {tag}", "iso_code": unique_iso()}).json()

    def city(country_id, name, lat, lng, nmin=1, nmax=3):
        return c.post(f"{API}/inventory/cities", json={"country_id": country_id, "name": f"{name}{tag}", "latitude": lat, "longitude": lng,
                                                       "recommended_nights_min": nmin, "recommended_nights_max": nmax}).json()

    nl, fr, ch = country("Holland"), country("Gaul"), country("Helvetia")
    ams = city(nl["id"], "Amster", 52.3676, 4.9041)
    par = city(fr["id"], "Paree", 48.8566, 2.3522, 2, 4)
    luc = city(ch["id"], "Luzern", 47.0502, 8.3093, 2, 3)
    zrh = city(ch["id"], "Zurik", 47.3769, 8.5417)
    for cty, name, cat, tags in [
        (ams, "Canal cruise", "tour", ["scenic", "family"]), (ams, "Big museum", "museum", ["museums"]),
        (par, "Iron tower", "landmark", ["historical_landmarks", "family"]), (par, "Art palace", "museum", ["museums"]),
        (luc, "Glacier mountain", "mountain", ["mountains", "scenic"]), (luc, "Lake cruise", "lake", ["lakes", "scenic"]),
        (zrh, "Old town", "landmark", ["historical_landmarks"]),
    ]:
        c.post(f"{API}/inventory/attractions", json={"city_id": cty["id"], "name": name, "category": cat, "interest_tags": tags,
                                                     "recommended_duration_min": 120, "child_friendly": True})
    hotels = {}
    for cty, stars in [(ams, 4), (par, 4), (par, 5), (luc, 4), (zrh, 4)]:
        h = c.post(f"{API}/inventory/hotels", json={"city_id": cty["id"], "name": f"Hotel {cty['name']} {stars}", "star_rating": stars,
                                                    "breakfast_available": True}).json()
        c.post(f"{API}/inventory/hotels/{h['id']}/room-types", json={"name": "Double", "max_occupancy": 2, "base_price": "150"})
        c.post(f"{API}/inventory/hotels/{h['id']}/room-types", json={"name": "Family room", "max_occupancy": 4, "base_price": "240"})
        hotels[(cty["id"], stars)] = h
    c.post(f"{API}/inventory/restaurants", json={"city_id": par["id"], "name": "Veg Paree", "vegetarian": True, "avg_price_per_person": "30"})
    cats = c.get(f"{API}/inventory/vehicle-categories").json()
    c.post(f"{API}/inventory/vehicles", json={"category_id": cats[2]["id"], "name": f"Minibus {tag}", "passenger_capacity": 16,
                                              "operating_country_ids": [nl["id"], fr["id"], ch["id"]], "price_per_day": "600"})
    return {"nl": nl, "fr": fr, "ch": ch, "ams": ams, "par": par, "luc": luc, "zrh": zrh, "hotels": hotels}


@pytest.fixture()
def enquiry(planner_client):
    agent = planner_client.post(f"{API}/travel-agents", json={"company_name": f"Gen Agency {_uid()}"}).json()
    cust = planner_client.post(f"{API}/customers", json={"travel_agent_id": agent["id"], "name": "Gen Family", "adults": 4, "children": 2, "children_ages": [8, 12]}).json()
    return planner_client.post(f"{API}/enquiries", json={"travel_agent_id": agent["id"], "customer_id": cust["id"], "adults": 4, "children": 2}).json()


def _requirements(world, **kw):
    body = {
        "adults": 4, "children": 2, "children_ages": [8, 12], "arrival_date": "2027-06-01", "departure_date": "2027-06-10",
        "arrival_airport": f"{world['ams']['name']} airport", "departure_airport": f"{world['zrh']['name']} airport",
        "destinations": [{"country_id": world[k]["id"], "preference": "mandatory"} for k in ("nl", "fr", "ch")],
        "interests": ["scenic", "mountains", "lakes", "family"], "hotel_categories": ["4_star"],
        "rooms": [{"type": "family", "count": 1}, {"type": "double", "count": 1}],
        "food_preferences": ["indian_vegetarian"], "meals": ["breakfast", "dinner"], "transport_modes": ["private_coach"],
        "budget_per_person": "2500",
    }
    body.update(kw)
    return body


def test_generation_requires_complete_requirements(planner_client, enquiry):
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate")
    assert r.status_code == 422 and r.json()["error"] == "requirements_missing"
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json={"adults": 2})
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate")
    assert r.status_code == 422 and r.json()["error"] == "requirements_incomplete" and "Arrival date" in r.json()["message"]


def test_generate_three_alternatives_end_to_end(planner_client, enquiry, world):
    assert planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world)).status_code == 200
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate")
    assert r.status_code == 201, r.text
    plans = r.json()
    assert [p["strategy"] for p in plans] == ["classic", "scenic", "premium"]
    for p in plans:
        assert p["total_days"] == 10 and p["total_nights"] == 9
        assert sum(s["nights"] for s in p["route"]) == 9
        assert p["route"][0]["city"] == world["ams"]["name"] and p["route"][-1]["city"] == world["zrh"]["name"]
        assert {s["city"] for s in p["route"]} >= {world["ams"]["name"], world["par"]["name"], world["zrh"]["name"]}
        assert p["version_number"] == 1 and p["version_label"] == "Generated" and p["batch"] == 1
        assert p["total_cost"] and p["enquiry_reference"] == enquiry["reference"]

    premium = planner_client.get(f"{API}/itineraries/{plans[2]['id']}").json()
    paris_stay = next(s for s in premium["stays"] if s["city"] == world["par"]["name"])
    assert paris_stay["hotel"]["stars"] == 5  # premium upgrades where a 5★ exists
    detail = planner_client.get(f"{API}/itineraries/{plans[0]['id']}").json()
    assert len(detail["days"]) == 10 and [d["day_number"] for d in detail["days"]] == list(range(1, 11))
    assert detail["days"][-1]["overnight_city"] is None
    # references real inventory records (not copies)
    assert all(s["hotel"]["id"] for s in detail["stays"])
    sights = [a for d in detail["days"] for a in d["activities"] if a["activity_type"] == "sightseeing"]
    assert sights and all(a["attraction_id"] for a in sights)
    veg = [m for d in detail["days"] for m in d["meals"] if m["restaurant_name"] == "Veg Paree"]
    assert veg, "verified vegetarian restaurant used in Paris"
    assert any("still to be arranged" in w for w in detail["warnings"])  # meals without a verified restaurant are flagged
    assert all(c["is_estimate"] for c in detail["costs"]) and detail["explanations"]
    assert any(t["kind"] == "intercity" and t["is_estimate"] and t["distance_km"] for t in detail["transports"])

    listed = planner_client.get(f"{API}/enquiries/{enquiry['id']}/itineraries").json()
    assert [p["id"] for p in listed] == [p["id"] for p in plans]
    assert planner_client.get(f"{API}/itineraries", params={"q": enquiry["reference"]}).json()["total"] == 3


def test_regeneration_creates_new_batch_and_skips_inactive_hotels(planner_client, admin_client, enquiry, world):
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world))
    first = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()
    hotel = world["hotels"][(world["par"]["id"], 4)]
    admin_client.patch(f"{API}/inventory/hotels/{hotel['id']}/status", json={"is_active": False})
    second = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()
    assert second[0]["batch"] == first[0]["batch"] + 1
    detail = planner_client.get(f"{API}/itineraries/{second[0]['id']}").json()
    assert hotel["id"] not in {s["hotel"]["id"] for s in detail["stays"] if s["hotel"]}
    listed = planner_client.get(f"{API}/enquiries/{enquiry['id']}/itineraries").json()
    assert listed[0]["batch"] == second[0]["batch"]  # latest first


def test_must_visits_that_cannot_fit_are_explained(planner_client, enquiry, world):
    body = _requirements(world, departure_date="2027-06-03")  # 2 nights, 4 must-visit stops incl. arrival/departure
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=body)
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate")
    assert r.status_code == 422 and r.json()["error"] == "cannot_generate"
    assert "only 2" in r.json()["message"]
    assert planner_client.get(f"{API}/enquiries/{enquiry['id']}/itineraries").json() == []


def test_itinerary_not_found(planner_client):
    assert planner_client.get(f"{API}/itineraries/999999").status_code == 404
