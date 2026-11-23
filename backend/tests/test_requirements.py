import uuid

import pytest

from tests.conftest import unique_iso

API = "/api/v1"


def _uid():
    return uuid.uuid4().hex[:6]


@pytest.fixture()
def world(admin_client):
    """Six countries with one city each (unique per test)."""
    countries, cities = [], []
    for name in ["Netherlands", "Belgium", "France", "Luxembourg", "Germany", "Switzerland"]:
        r = admin_client.post(f"{API}/inventory/countries", json={"name": f"{name} {_uid()}", "iso_code": unique_iso()})
        assert r.status_code == 201, r.text
        c = r.json()
        countries.append(c)
        cities.append(admin_client.post(f"{API}/inventory/cities", json={"country_id": c["id"], "name": f"City {_uid()}"}).json())
    return countries, cities


@pytest.fixture()
def enquiry(planner_client):
    agent = planner_client.post(f"{API}/travel-agents", json={"company_name": f"Req Agency {_uid()}"}).json()
    customer = planner_client.post(f"{API}/customers", json={
        "travel_agent_id": agent["id"], "name": "Sharma Family", "adults": 4, "children": 2, "children_ages": [9, 13]}).json()
    return planner_client.post(f"{API}/enquiries", json={
        "travel_agent_id": agent["id"], "customer_id": customer["id"], "adults": 4, "children": 2,
        "travel_start_date": "2027-06-01", "travel_end_date": "2027-06-15",
        "budget_amount": "3000", "budget_basis": "per_person", "budget_currency": "EUR"}).json()


def test_defaults_prefilled_from_enquiry_and_customer(planner_client, enquiry):
    r = planner_client.get(f"{API}/enquiries/{enquiry['id']}/requirements").json()
    assert r["exists"] is False
    assert (r["adults"], r["children"], r["children_ages"]) == (4, 2, [9, 13])
    assert r["arrival_date"] == "2027-06-01" and r["total_days"] == 15 and r["total_nights"] == 14
    assert r["budget_per_person"] == "3000.00" and r["meals"] == ["breakfast"]
    assert "Arrival airport / city" in r["missing"] and "At least one destination to visit" in r["missing"]
    assert r["is_complete"] is False


def test_prd_part28_scenario_saves_complete_and_syncs_enquiry(planner_client, enquiry, world):
    countries, cities = world
    body = {
        "adults": 4, "children": 2, "children_ages": [9, 13],
        "arrival_date": "2027-06-01", "departure_date": "2027-06-15",
        "arrival_airport": "Amsterdam (AMS)", "departure_airport": "Zurich (ZRH)",
        "start_country_id": countries[0]["id"], "end_country_id": countries[5]["id"],
        "travel_type": "FIT",
        "destinations": [
            {"country_id": c["id"], "preference": "mandatory" if i in (0, 2, 5) else "preferred"} for i, c in enumerate(countries)
        ] + [{"country_id": countries[0]["id"], "city_id": cities[0]["id"], "preference": "mandatory", "min_nights": 2}],
        "interests": ["scenic", "lakes", "mountains", "family"], "travel_pace": "balanced",
        "hotel_categories": ["4_star"], "hotel_locations": ["city_centre"], "breakfast_required": True,
        "rooms": [{"type": "family", "count": 1}, {"type": "double", "count": 1}],
        "food_preferences": ["indian_vegetarian"], "meals": ["dinner", "breakfast"],
        "transport_modes": ["private_coach"], "passenger_capacity": 16, "airport_transfers": True,
        "budget_per_person": "3000", "currency": "eur", "budget_flexibility": "some", "travel_class": "standard",
        "additional_requirements": "Celebrating a birthday on day 5", "internal_notes": "Agent prefers WhatsApp",
        "completed_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 42],
    }
    r = planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=body)
    assert r.status_code == 200, r.text
    req = r.json()
    assert req["exists"] and req["is_complete"] and req["missing"] == []
    assert req["total_days"] == 15 and req["total_nights"] == 14 and req["total_travellers"] == 6
    assert req["rooms_count"] == 2 and req["room_capacity"] == 6
    assert req["meals"] == ["breakfast", "dinner"] and req["currency"] == "EUR"
    assert req["completed_steps"] == list(range(1, 10))
    assert len(req["destinations"]) == 7 and req["destinations"][-1]["city"]["id"] == cities[0]["id"]
    assert req["warnings"] == []

    # retrieved later exactly as saved (PRD Phase 3 acceptance)
    again = planner_client.get(f"{API}/enquiries/{enquiry['id']}/requirements").json()
    assert again["destinations"] == req["destinations"] and again["interests"] == req["interests"]

    # enquiry summary synced and status moved to In Progress (recorded)
    e = planner_client.get(f"{API}/enquiries/{enquiry['id']}").json()
    assert e["status"] == "in_progress" and e["status_history"][-1]["note"] == "Requirement capture started"
    assert e["budget_amount"] == "3000.00" and e["budget_basis"] == "per_person"


def test_draft_save_reports_missing_without_failing(planner_client, enquiry):
    r = planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json={"adults": 2, "completed_steps": [1]})
    assert r.status_code == 200
    body = r.json()
    assert body["exists"] and not body["is_complete"]
    assert {"Arrival date", "Departure date", "Budget"} <= set(body["missing"])
    # enquiry travellers updated from requirements
    assert planner_client.get(f"{API}/enquiries/{enquiry['id']}").json()["total_travellers"] == 2


def test_conflicts_are_flagged_not_dropped(planner_client, enquiry, world):
    countries, cities = world
    body = {
        "adults": 6, "arrival_date": "2027-06-01", "departure_date": "2027-06-03",
        "start_country_id": countries[1]["id"],
        "destinations": [
            {"country_id": countries[0]["id"], "preference": "mandatory", "min_nights": 2},
            {"country_id": countries[2]["id"], "preference": "mandatory"},
            {"country_id": countries[3]["id"], "preference": "mandatory"},
            {"country_id": countries[1]["id"], "preference": "avoid"},
        ],
        "rooms": [{"type": "double", "count": 1}], "passenger_capacity": 4,
        "budget_per_person": "1000", "budget_total": "20000", "food_preferences": ["indian_jain"],
    }
    req = planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=body).json()
    text = " | ".join(req["warnings"])
    assert "3 must-visit destinations but only 2 nights" in text
    assert "Starting country is also marked as a country to avoid" in text
    assert "Rooms sleep 2 but there are 6 travellers" in text
    assert "Vehicle capacity (4)" in text
    assert "does not match the group total" in text
    assert "verified Jain" in text
    assert len(req["destinations"]) == 4  # nothing silently removed


@pytest.mark.parametrize("patch, message", [
    ({"children": 1, "children_ages": []}, "age for each child"),
    ({"arrival_date": "2027-06-10", "departure_date": "2027-06-01"}, "Departure date cannot be before"),
    ({"interests": ["gambling"]}, "Unknown interests"),
    ({"rooms": [{"type": "palace", "count": 1}]}, "Unknown room type"),
    ({"food_preferences": ["paleo"]}, "Unknown food preferences"),
])
def test_validation_messages(planner_client, enquiry, patch, message):
    r = planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json={"adults": 2, **patch})
    assert r.status_code == 422 and message in r.json()["details"][0]["message"]


def test_city_must_belong_to_country_and_duplicates_rejected(planner_client, enquiry, world):
    countries, cities = world
    wrong = planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json={
        "adults": 2, "destinations": [{"country_id": countries[0]["id"], "city_id": cities[1]["id"], "preference": "preferred"}]})
    assert wrong.status_code == 400 and wrong.json()["error"] == "city_country_mismatch"
    dup = planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json={
        "adults": 2, "destinations": [{"country_id": countries[0]["id"], "preference": "preferred"}] * 2})
    assert dup.status_code == 422


def test_options_and_not_found(planner_client):
    opts = planner_client.get(f"{API}/enquiries/requirements/options").json()
    assert "indian_jain" in opts["food_preferences"] and opts["preferences"] == ["mandatory", "preferred", "optional", "avoid"]
    assert planner_client.get(f"{API}/enquiries/999999/requirements").status_code == 404
