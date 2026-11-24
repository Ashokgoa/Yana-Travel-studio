"""AI assistant (Phase 8): offline reader, provider fallback, itinerary suggestions."""

from datetime import date

import pytest

from app.engines.text_extract import ExtractedRequirements, extract
from tests.test_itineraries import API, _requirements, enquiry, world  # noqa: F401  (fixtures)

TODAY = date(2026, 11, 24)
COUNTRIES = ["Netherlands", "Belgium", "France", "Germany", "Switzerland", "Austria", "Italy", "Luxembourg"]
CITIES = ["Amsterdam", "Brussels", "Paris", "Lucerne", "Zurich", "Interlaken", "Cochem"]
EMAIL = """Dear YANA team,
We have a family of 6 (4 adults and 2 kids aged 8 & 12) looking for a 15 days Europe tour.
They arrive in Amsterdam on 1st June 2027 and fly out of Zurich. Must cover Holland, Belgium, Paris, Germany and Switzerland, ideally Lucerne.
4* hotels please, 2 double rooms + 1 family room. Pure veg Indian food, Jain for grandmother. Breakfast and dinner included.
Private coach. They love castles, lakes and shopping, relaxed pace. Budget around EUR 3,000 per person.
One senior needs wheelchair assistance at airports."""


# ------------------------------------------------------------------ offline reader (unit)
def test_offline_reader_on_a_typical_agent_email():
    r = extract(EMAIL, today=TODAY, known_countries=COUNTRIES, known_cities=CITIES)
    assert (r.adults, r.children, r.children_ages) == (4, 2, [8, 12])
    assert (r.arrival_date, r.departure_date) == (date(2027, 6, 1), date(2027, 6, 15))
    assert (r.arrival_place, r.departure_place) == ("Amsterdam", "Zurich")
    assert set(r.countries) == {"Belgium", "Germany", "Switzerland", "Netherlands"}  # Holland -> Netherlands
    assert r.cities == ["Amsterdam", "Zurich", "Paris", "Lucerne"]
    assert r.hotel_categories == ["4_star"]
    assert [(x.type, x.count) for x in r.rooms] == [("double", 2), ("family", 1)]
    assert set(r.food_preferences) == {"indian_jain", "indian_vegetarian"}
    assert r.meals == ["breakfast", "dinner"] and r.transport_modes == ["private_coach"] and r.travel_pace == "relaxed"
    assert {"historical_landmarks", "lakes", "shopping"} <= set(r.interests)
    assert (r.budget_per_person, r.budget_total, r.currency) == (3000.0, None, "EUR")
    assert r.special_requests == ["One senior needs wheelchair assistance at airports"]
    assert {e.field for e in r.evidence} >= {"adults", "arrival_date", "budget_per_person"}


@pytest.mark.parametrize("text,check", [
    ("Group of 20 pax, GIT, June 5-16 2027, 12D/11N, mini bus, non-veg and veg meals, all meals",
     lambda r: r.adults == 20 and r.travel_type == "GIT" and r.arrival_date == date(2027, 6, 5) and r.departure_date == date(2027, 6, 16)
     and r.transport_modes == ["mini_bus"] and set(r.food_preferences) == {"indian_non_vegetarian", "indian_vegetarian"} and r.meals == ["breakfast", "lunch", "dinner"]),
    ("Couple, 2 adults, arriving 10/09/2027 for 7 nights. Budget Rs 2,50,000 per person, 5 star luxury, Benelux.",
     lambda r: r.adults == 2 and r.arrival_date == date(2027, 9, 10) and r.departure_date == date(2027, 9, 17)
     and r.currency == "INR" and r.budget_per_person == 250000 and r.hotel_categories == ["5_star", "luxury"]
     and set(r.countries) == {"Belgium", "Netherlands", "Luxembourg"}),
    ("Three adults, total budget 9000 euros, March 3, train between cities, fast-paced, Swiss Alps",
     lambda r: r.adults == 3 and r.budget_total == 9000 and r.currency == "EUR" and r.arrival_date == date(2027, 3, 3)
     and r.transport_modes == ["train"] and r.travel_pace == "fast" and "Switzerland" in r.countries and "mountains" in r.interests),
    ("Hello, please share options.", lambda r: r.adults is None and not r.countries and r.arrival_date is None and r.budget_total is None),
])
def test_offline_reader_variants(text, check):
    assert check(extract(text, today=TODAY, known_countries=COUNTRIES, known_cities=CITIES))


# ------------------------------------------------------------------ read-text API
def _email_for(world):
    return (f"Family of 6: 4 adults and 2 kids aged 8 and 12. Arrive {world['ams']['name']} on 2 June 2027, "
            f"leave from {world['zrh']['name']} on 11 June 2027. Must see {world['par']['name']}, {world['luc']['name']} and Prague. "
            "4 star hotels, Jain food, budget EUR 2,800 per person. Celebrating an anniversary.")


def test_read_text_proposes_fields_without_saving(planner_client, enquiry, world):  # noqa: F811
    st = planner_client.get(f"{API}/ai/status").json()
    assert st["provider"] == "offline" and st["sends_data_off_device"] is False
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/requirements/read-text", json={"text": _email_for(world)})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["provider"] == "offline" and not res["sends_data_off_device"] and res["fallback_note"] is None
    s = {x["field"]: x for x in res["suggestions"]}
    assert "children_ages" not in s  # already copied from the customer record
    assert s["arrival_date"]["value"] == "2027-06-02" and s["departure_date"]["value"] == "2027-06-11"
    assert s["arrival_airport"]["value"] == world["ams"]["name"] and s["start_country_id"]["value"] == world["nl"]["id"]
    assert s["end_country_id"]["value"] == world["ch"]["id"]
    dests = s["destinations"]["value"]
    assert {d["city_id"] for d in dests} >= {world["par"]["id"], world["luc"]["id"]} and all(d["preference"] == "mandatory" for d in dests)
    assert s["food_preferences"]["value"] == ["indian_jain"] and s["hotel_categories"]["value"] == ["4_star"]
    assert s["budget_per_person"]["value"] == "2800.00" and "anniversary" in s["additional_requirements"]["value"].lower()
    assert "Prague" in res["unmatched_places"]
    assert s["arrival_date"]["evidence"] and not s["arrival_date"]["overwrites"]
    # Nothing was saved.
    req = planner_client.get(f"{API}/enquiries/{enquiry['id']}/requirements").json()
    assert req["arrival_date"] is None and req["destinations"] == []

    # With saved requirements, differing values are flagged as overwrites and equal ones are not suggested.
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world))
    res = planner_client.post(f"{API}/enquiries/{enquiry['id']}/requirements/read-text", json={"text": _email_for(world)}).json()
    s = {x["field"]: x for x in res["suggestions"]}
    assert s["arrival_date"]["overwrites"] and s["arrival_date"]["current"] == "01 Jun 2027"
    assert "children_ages" not in s  # already [8, 12]
    assert planner_client.post(f"{API}/enquiries/{enquiry['id']}/requirements/read-text", json={"text": "hi"}).status_code == 422


def test_claude_provider_failure_falls_back_to_offline(planner_client, enquiry, world, monkeypatch):  # noqa: F811
    from app.services import ai_service
    from app.services.ai_provider import AIProvider, AIUnavailable

    class Failing(AIProvider):
        name, label, sends_data_off_device = "claude", "Claude (test)", True

        def extract_requirements(self, text, **kw):
            raise AIUnavailable("Cannot reach the Claude API from this computer.")

    monkeypatch.setattr(ai_service, "get_provider", lambda: Failing())
    res = planner_client.post(f"{API}/enquiries/{enquiry['id']}/requirements/read-text", json={"text": _email_for(world)}).json()
    assert res["provider"] == "offline" and "Cannot reach the Claude API" in res["fallback_note"] and res["suggestions"]

    class Fake(AIProvider):
        name, label, sends_data_off_device = "claude", "Claude (test)", True

        def extract_requirements(self, text, **kw):
            return ExtractedRequirements(adults=7, cities=[world["par"]["name"]])

    monkeypatch.setattr(ai_service, "get_provider", lambda: Fake())
    res = planner_client.post(f"{API}/enquiries/{enquiry['id']}/requirements/read-text", json={"text": _email_for(world)}).json()
    assert res["provider"] == "claude" and res["sends_data_off_device"] is True
    assert {x["field"]: x["value"] for x in res["suggestions"]}["adults"] == 7


def test_claude_provider_is_off_unless_configured(monkeypatch):
    from app.services import ai_provider

    assert isinstance(ai_provider.get_provider(), ai_provider.OfflineProvider)
    settings = ai_provider.get_settings()
    monkeypatch.setattr(settings, "ai_provider", "claude")
    monkeypatch.setattr(ai_provider, "anthropic_installed", lambda: False)
    assert isinstance(ai_provider.get_provider(), ai_provider.OfflineProvider)  # SDK missing: stays offline
    monkeypatch.setattr(ai_provider, "anthropic_installed", lambda: True)
    p = ai_provider.get_provider()
    assert isinstance(p, ai_provider.ClaudeProvider) and p.model == "claude-opus-5-5" and p.sends_data_off_device


# ------------------------------------------------------------------ itinerary suggestions
@pytest.fixture()
def itinerary(planner_client, enquiry, world):  # noqa: F811
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements",
                       json=_requirements(world, food_preferences=["indian_vegetarian"], meals=["breakfast", "lunch", "dinner"]))
    return planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()[0]


def _sugg(c, iid):
    return c.get(f"{API}/itineraries/{iid}/suggestions").json()


def test_suggestions_duplicate_free_day_diet_hotel_and_apply(planner_client, admin_client, itinerary, world):
    iid = itinerary["id"]
    d = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    # 1. duplicate: add a sightseeing that is already on another day
    first = next(x for x in d["days"] if any(a["attraction_id"] for a in x["activities"]))
    att = next(a for a in first["activities"] if a["attraction_id"])
    other = next(x for x in d["days"] if x["city_id"] == first["city_id"] and x["day_number"] != first["day_number"])
    planner_client.post(f"{API}/itineraries/{iid}/days/{other['day_number']}/activities", json={"time_slot": "evening", "attraction_id": att["attraction_id"]})
    s = _sugg(planner_client, iid)
    dup = next(x for x in s if x["kind"] == "duplicate")
    assert dup["action"]["op"] == "remove_activity"
    after = planner_client.post(f"{API}/itineraries/{iid}/suggestions/apply", json={"key": dup["key"]}).json()
    assert sum(a["attraction_id"] == att["attraction_id"] for x in after["days"] for a in x["activities"]) == 1
    assert not any(x["kind"] == "duplicate" for x in _sugg(planner_client, iid))

    # 2. free day: add a day in Paris and an unused Paris sightseeing matching the interests
    paris_day = next(x for x in after["days"] if x["city_id"] == world["par"]["id"] and x["overnight_city"])
    planner_client.post(f"{API}/itineraries/{iid}/days/{paris_day['day_number']}/add-after")
    admin_client.post(f"{API}/inventory/attractions", json={"city_id": world["par"]["id"], "name": "Seine viewpoint", "category": "landmark",
                                                            "interest_tags": ["scenic", "lakes"], "recommended_duration_min": 60, "child_friendly": True})
    free = next(x for x in _sugg(planner_client, iid) if x["kind"] == "free_day")
    assert free["action"]["day"] == paris_day["day_number"] + 1
    after = planner_client.post(f"{API}/itineraries/{iid}/suggestions/apply", json={"key": free["key"]}).json()
    day = next(x for x in after["days"] if x["day_number"] == paris_day["day_number"] + 1)
    assert any(a["attraction_id"] == free["action"]["attraction_id"] for a in day["activities"])

    # 3. diet: a Paris lunch at a restaurant without a verified vegetarian option
    meat = admin_client.post(f"{API}/inventory/restaurants", json={"city_id": world["par"]["id"], "name": "Grill Paree", "cuisine": "French"}).json()
    planner_client.put(f"{API}/itineraries/{iid}/days/{paris_day['day_number']}/meals/lunch", json={"arrangement": "restaurant", "restaurant_id": meat["id"]})
    diet = next(x for x in _sugg(planner_client, iid) if x["kind"] == "diet")
    assert "Veg Paree" in diet["title"] and "no verified vegetarian" in diet["reason"]
    after = planner_client.post(f"{API}/itineraries/{iid}/suggestions/apply", json={"key": diet["key"]}).json()
    lunch = next(m for m in next(x for x in after["days"] if x["day_number"] == paris_day["day_number"])["meals"] if m["meal"] == "lunch")
    assert lunch["restaurant_name"] == "Veg Paree"

    # 4. hotel below the requested 4 stars
    cheap = admin_client.post(f"{API}/inventory/hotels", json={"city_id": world["par"]["id"], "name": "Budget Paree", "star_rating": 3}).json()
    admin_client.post(f"{API}/inventory/hotels/{cheap['id']}/room-types", json={"name": "Double", "max_occupancy": 2, "base_price": "90"})
    stay = next(x for x in after["stays"] if x["city_id"] == world["par"]["id"])
    planner_client.put(f"{API}/itineraries/{iid}/stays/{stay['id']}/hotel", json={"hotel_id": cheap["id"]})
    hotel = next(x for x in _sugg(planner_client, iid) if x["kind"] == "hotel_category")
    assert "4★ or better" in hotel["reason"]
    after = planner_client.post(f"{API}/itineraries/{iid}/suggestions/apply", json={"key": hotel["key"]}).json()
    assert next(x for x in after["stays"] if x["city_id"] == world["par"]["id"])["hotel"]["stars"] >= 4

    # stale key
    r = planner_client.post(f"{API}/itineraries/{iid}/suggestions/apply", json={"key": hotel["key"]})
    assert r.status_code == 409 and r.json()["error"] == "suggestion_stale"


def test_apply_on_a_saved_version_starts_a_working_copy(planner_client, admin_client, itinerary, world):
    iid = itinerary["id"]
    admin_client.post(f"{API}/inventory/restaurants", json={"city_id": world["par"]["id"], "name": "Steak Paree"})
    d = planner_client.get(f"{API}/itineraries/{iid}").json()
    assert d["is_locked"]
    # Make the generated version need a suggestion by editing, saving, then applying on the locked latest version.
    planner_client.post(f"{API}/itineraries/{iid}/edit")
    paris = next(x for x in d["days"] if x["city_id"] == world["par"]["id"] and x["overnight_city"])
    rest = next(r for r in planner_client.get(f"{API}/inventory/restaurants", params={"city_id": world["par"]["id"]}).json()["items"] if r["name"] == "Steak Paree")
    planner_client.put(f"{API}/itineraries/{iid}/days/{paris['day_number']}/meals/dinner", json={"arrangement": "restaurant", "restaurant_id": rest["id"]})
    planner_client.post(f"{API}/itineraries/{iid}/versions", json={"label": "Steak dinner"})
    diet = next(x for x in _sugg(planner_client, iid) if x["kind"] == "diet")
    after = planner_client.post(f"{API}/itineraries/{iid}/suggestions/apply", json={"key": diet["key"]}).json()
    assert not after["is_locked"] and after["version_number"] == 3  # v2 kept as saved; change made on a new working copy
