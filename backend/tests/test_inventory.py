import uuid

import pytest

API = "/api/v1/inventory"


def _uid() -> str:
    return uuid.uuid4().hex[:6]


def _country(c, **kw):
    iso = kw.pop("iso_code", None) or "".join(chr(65 + (b % 26)) for b in uuid.uuid4().bytes[:2])
    r = c.post(f"{API}/countries", json={"name": f"Country {_uid()}", "iso_code": iso, "region": "Western Europe", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def _city(c, country_id, **kw):
    r = c.post(f"{API}/cities", json={"country_id": country_id, "name": f"City {_uid()}", "latitude": 52.37, "longitude": 4.9, **kw})
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ permissions
def test_planner_can_read_but_not_write(planner_client, admin_client):
    country = _country(admin_client)
    assert planner_client.get(f"{API}/countries").status_code == 200
    assert planner_client.get(f"{API}/countries/{country['id']}").status_code == 200
    r = planner_client.post(f"{API}/countries", json={"name": "X", "iso_code": "QX"})
    assert r.status_code == 403
    assert planner_client.patch(f"{API}/countries/{country['id']}/status", json={"is_active": False}).status_code == 403


def test_inventory_requires_login(client):
    assert client.get(f"{API}/hotels").status_code == 401


# ------------------------------------------------------------------ countries & cities (PRD: add destinations without code changes)
def test_add_country_and_city_without_code_changes(admin_client):
    country = _country(admin_client, iso_code="pt")
    assert country["iso_code"] == "PT"
    city = _city(admin_client, country["id"], name="Lisbon", recommended_nights_min=2, recommended_nights_max=3)
    assert city["country"]["id"] == country["id"]
    got = admin_client.get(f"{API}/countries/{country['id']}").json()
    assert got["city_count"] == 1
    listed = admin_client.get(f"{API}/cities", params={"country_id": country["id"]}).json()
    assert [x["name"] for x in listed["items"]] == ["Lisbon"]


def test_duplicate_country_and_city_rejected(admin_client):
    country = _country(admin_client, iso_code="MT", name=f"Malta {_uid()}")
    r = admin_client.post(f"{API}/countries", json={"name": "Another", "iso_code": "MT"})
    assert r.status_code == 409
    _city(admin_client, country["id"], name="Valletta")
    r = admin_client.post(f"{API}/cities", json={"country_id": country["id"], "name": "Valletta"})
    assert r.status_code == 409 and "already has a city" in r.json()["message"]


@pytest.mark.parametrize("payload, message", [
    ({"latitude": 95, "longitude": 4}, "less than or equal to 90"),
    ({"latitude": 52.1}, "both latitude and longitude"),
    ({"recommended_nights_min": 3, "recommended_nights_max": 1}, "cannot be less than"),
])
def test_city_validation(admin_client, payload, message):
    country = _country(admin_client)
    r = admin_client.post(f"{API}/cities", json={"country_id": country["id"], "name": "X", **payload})
    assert r.status_code == 422 and message in r.json()["details"][0]["message"]


def test_unknown_reference_rejected(admin_client):
    r = admin_client.post(f"{API}/cities", json={"country_id": 999999, "name": "Nowhere"})
    assert r.status_code == 400 and r.json()["error"] == "invalid_reference"


def test_deactivate_and_filter_active(admin_client):
    country = _country(admin_client)
    city = _city(admin_client, country["id"])
    admin_client.patch(f"{API}/cities/{city['id']}/status", json={"is_active": False})
    active = admin_client.get(f"{API}/cities", params={"country_id": country["id"], "active": "true"}).json()
    assert active["total"] == 0
    everything = admin_client.get(f"{API}/cities", params={"country_id": country["id"]}).json()
    assert everything["total"] == 1 and everything["items"][0]["is_active"] is False


# ------------------------------------------------------------------ attractions
def test_attraction_with_tags_days_and_country_filter(admin_client):
    country = _country(admin_client)
    city = _city(admin_client, country["id"])
    r = admin_client.post(f"{API}/attractions", json={
        "city_id": city["id"], "name": "Rijksmuseum", "category": "museum",
        "interest_tags": ["museums", "cultural", "museums"], "operating_days": ["SUN", "mon"],
        "recommended_duration_min": 180, "ticket_required": True, "ticket_price": "25.00", "child_friendly": True,
    })
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["interest_tags"] == ["museums", "cultural"] and a["operating_days"] == ["mon", "sun"]
    assert a["price_is_verified"] is False and a["city"]["country"]["id"] == country["id"]
    by_country = admin_client.get(f"{API}/attractions", params={"country_id": country["id"]}).json()
    assert [x["id"] for x in by_country["items"]] == [a["id"]]
    assert admin_client.get(f"{API}/attractions", params={"q": "rijks"}).json()["total"] >= 1


def test_attraction_rejects_unknown_vocabulary(admin_client):
    country = _country(admin_client)
    city = _city(admin_client, country["id"])
    r = admin_client.post(f"{API}/attractions", json={"city_id": city["id"], "name": "X", "category": "casino"})
    assert r.status_code == 422
    r = admin_client.post(f"{API}/attractions", json={"city_id": city["id"], "name": "X", "category": "museum", "interest_tags": ["gambling"]})
    assert r.status_code == 422 and "gambling" in r.json()["details"][0]["message"]


# ------------------------------------------------------------------ hotels, room types, seasonal rates
def test_hotel_room_types_and_rates(admin_client, planner_client):
    country = _country(admin_client)
    city = _city(admin_client, country["id"])
    hotel = admin_client.post(f"{API}/hotels", json={
        "city_id": city["id"], "name": "Demo Canal Hotel", "star_rating": 4, "style_tags": ["boutique"],
        "facilities": ["wifi", "lift"], "breakfast_available": True, "location_type": "city_centre", "is_demo": True,
    }).json()
    assert hotel["is_demo"] is True and hotel["room_types"] == []

    h = admin_client.post(f"{API}/hotels/{hotel['id']}/room-types", json={"name": "Double", "max_occupancy": 2, "base_price": "180"}).json()
    rt = h["room_types"][0]
    assert rt["price_is_verified"] is False

    r = admin_client.post(f"{API}/hotels/{hotel['id']}/rates", json={
        "room_type_id": rt["id"], "season_name": "Summer", "valid_from": "2027-06-01", "valid_to": "2027-08-31", "price": "210"})
    assert r.status_code == 200 and r.json()["rates"][0]["season_name"] == "Summer"

    bad = admin_client.post(f"{API}/hotels/{hotel['id']}/rates", json={
        "room_type_id": rt["id"], "season_name": "X", "valid_from": "2027-09-01", "valid_to": "2027-08-01", "price": "1"})
    assert bad.status_code == 422

    assert planner_client.post(f"{API}/hotels/{hotel['id']}/room-types", json={"name": "Suite"}).status_code == 403

    four_star = admin_client.get(f"{API}/hotels", params={"city_id": city["id"], "star_rating": 4}).json()
    assert four_star["total"] == 1
    after = admin_client.delete(f"{API}/hotels/{hotel['id']}/room-types/{rt['id']}").json()
    assert after["room_types"] == [] and after["rates"] == []


def test_rate_must_use_room_type_of_same_hotel(admin_client):
    country = _country(admin_client)
    city = _city(admin_client, country["id"])
    h1 = admin_client.post(f"{API}/hotels", json={"city_id": city["id"], "name": "H1"}).json()
    h2 = admin_client.post(f"{API}/hotels", json={"city_id": city["id"], "name": "H2"}).json()
    rt = admin_client.post(f"{API}/hotels/{h1['id']}/room-types", json={"name": "Double"}).json()["room_types"][0]
    r = admin_client.post(f"{API}/hotels/{h2['id']}/rates", json={
        "room_type_id": rt["id"], "season_name": "S", "valid_from": "2027-01-01", "valid_to": "2027-01-31", "price": "1"})
    assert r.status_code == 404


# ------------------------------------------------------------------ restaurants: dietary flags never assumed
def test_restaurant_dietary_unknown_by_default_and_filter_only_verified(admin_client):
    country = _country(admin_client)
    city = _city(admin_client, country["id"])
    unknown = admin_client.post(f"{API}/restaurants", json={"city_id": city["id"], "name": "Unknown Bistro"}).json()
    assert unknown["jain"] is None and unknown["vegetarian"] is None
    jain = admin_client.post(f"{API}/restaurants", json={
        "city_id": city["id"], "name": "Demo Jain Kitchen", "jain": True, "vegetarian": True, "price_range": "€€"}).json()
    result = admin_client.get(f"{API}/restaurants", params={"city_id": city["id"], "jain": "true"}).json()
    assert [x["id"] for x in result["items"]] == [jain["id"]]
    assert admin_client.post(f"{API}/restaurants", json={"city_id": city["id"], "name": "X", "price_range": "cheap"}).status_code == 422


# ------------------------------------------------------------------ vehicles & suppliers
def test_vehicle_with_categories_countries_and_supplier(admin_client):
    cats = admin_client.get(f"{API}/vehicle-categories").json()
    assert [c["name"] for c in cats][:2] == ["7-seater", "9-seater"] and len(cats) == 7
    country = _country(admin_client)
    supplier = admin_client.post(f"{API}/suppliers", json={"name": "Demo Coaches BV", "supplier_type": "coach", "is_demo": True}).json()
    r = admin_client.post(f"{API}/vehicles", json={
        "category_id": cats[4]["id"], "name": "40-seat touring coach", "passenger_capacity": 40, "supplier_id": supplier["id"],
        "service_types": ["intercity", "local"], "operating_country_ids": [country["id"]], "price_per_day": "850"})
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["operating_countries"][0]["id"] == country["id"] and v["supplier"]["name"] == "Demo Coaches BV"
    bad = admin_client.post(f"{API}/vehicles", json={"category_id": cats[0]["id"], "name": "X", "passenger_capacity": 7, "operating_country_ids": [999999]})
    assert bad.status_code == 400
    by_type = admin_client.get(f"{API}/suppliers", params={"supplier_type": "coach"}).json()
    assert supplier["id"] in [s["id"] for s in by_type["items"]]


def test_invalid_filter_value_reports_error(admin_client):
    r = admin_client.get(f"{API}/hotels", params={"star_rating": "five"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_filter"


def test_options_vocabularies(planner_client):
    opts = planner_client.get(f"{API}/options").json()
    assert "museum" in opts["attraction_categories"] and "jain" not in opts["interest_tags"]
    assert opts["weekdays"][0] == "mon"
