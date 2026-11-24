"""Supplier rate cards and per-line supplier quotes (Phase 8c)."""

from decimal import Decimal as D

import pytest

from tests.test_itineraries import API, _requirements, _uid, enquiry, world  # noqa: F401  (fixtures)


@pytest.fixture()
def itinerary(planner_client, enquiry, world):  # noqa: F811
    body = _requirements(world)
    body.pop("budget_per_person")  # itinerary first, budget later
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=body)
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]})
    assert r.status_code == 201, r.text
    return r.json()[0]


@pytest.fixture()
def coach_supplier(admin_client):
    return admin_client.post(f"{API}/inventory/suppliers", json={"name": f"Alpine Coaches {_uid()}", "supplier_type": "coach"}).json()


def test_rate_card_crud_and_search(planner_client, coach_supplier):
    sid = coach_supplier["id"]
    base = {"service": "16-seat coach with driver", "category": "transport", "basis": "per_day", "unit_cost": "520", "currency": "CHF"}
    summer = planner_client.post(f"{API}/suppliers/{sid}/rates", json={**base, "valid_from": "2027-05-01", "valid_to": "2027-09-30"})
    assert summer.status_code == 201, summer.text
    winter = planner_client.post(f"{API}/suppliers/{sid}/rates", json={**base, "unit_cost": "450", "valid_from": "2027-10-01", "valid_to": "2028-03-31"}).json()
    bad = planner_client.post(f"{API}/suppliers/{sid}/rates", json={**base, "valid_from": "2027-09-01", "valid_to": "2027-08-01"})
    assert bad.status_code == 422
    assert len(planner_client.get(f"{API}/suppliers/{sid}/rates").json()) == 2
    found = [r for r in planner_client.get(f"{API}/supplier-rates", params={"category": "transport", "on": "2027-06-10", "supplier_id": sid}).json()]
    assert found[0]["id"] == summer.json()["id"] and found[0]["valid_on_trip"] is True and found[1]["valid_on_trip"] is False
    assert found[0]["supplier_name"] == coach_supplier["name"]
    upd = planner_client.put(f"{API}/supplier-rates/{winter['id']}", json={**base, "unit_cost": "430"}).json()
    assert D(upd["unit_cost"]) == 430 and upd["valid_from"] is None
    assert planner_client.delete(f"{API}/supplier-rates/{winter['id']}").status_code == 204
    assert planner_client.get(f"{API}/suppliers/999999/rates").status_code == 404


def test_quote_from_rate_in_other_currency_with_status_and_progress(planner_client, itinerary, coach_supplier):
    iid = itinerary["id"]
    p = planner_client.get(f"{API}/itineraries/{iid}/pricing").json()
    assert p["quote_progress"]["total"] >= 1 and p["quote_progress"]["confirmed"] == 0
    vehicle = next(l for l in p["lines"] if l["key"].startswith("vehicle:") and l["key"].endswith(":day"))
    assert vehicle["status"] == "estimate"
    rate = planner_client.post(f"{API}/suppliers/{coach_supplier['id']}/rates",
                               json={"service": "Minibus per day", "category": "transport", "basis": "per_day", "unit_cost": "500", "currency": "CHF"}).json()

    no_fx = planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={"key": vehicle["key"], "amount": "500", "currency": "CHF"})
    assert no_fx.status_code == 400 and no_fx.json()["error"] == "fx_required"
    q = planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={
        "key": vehicle["key"], "supplier_id": coach_supplier["id"], "supplier_rate_id": rate["id"], "amount": "500", "currency": "CHF",
        "fx_rate": "1.05", "status": "quoted", "reference": "Email 24 Nov"}).json()
    line = next(l for l in q["lines"] if l["key"] == vehicle["key"])
    assert line["unit_cost"] == "525.00" and line["status"] == "quoted" and line["supplier_name"] == coach_supplier["name"]
    assert line["quote"]["amount"] == "500" and line["quote"]["currency"] == "CHF" and line["quote"]["reference"] == "Email 24 Nov"
    assert q["fx_rates"] == {"CHF": "1.05"}
    assert D(line["total"]) == D("525") * D(line["quantity"])

    # The saved exchange rate is reused; confirming moves the progress.
    q = planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={
        "key": vehicle["key"], "supplier_id": coach_supplier["id"], "amount": "480", "currency": "CHF", "status": "confirmed"}).json()
    line = next(l for l in q["lines"] if l["key"] == vehicle["key"])
    assert line["unit_cost"] == "504.00" and line["status"] == "confirmed" and q["quote_progress"]["confirmed"] == 1
    usd = planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={"key": vehicle["key"], "amount": "10", "currency": "USD"})
    assert usd.status_code == 400

    # Back to the inventory estimate.
    q = planner_client.delete(f"{API}/itineraries/{iid}/pricing/quote", params={"key": vehicle["key"]}).json()
    line = next(l for l in q["lines"] if l["key"] == vehicle["key"])
    assert line["status"] == "estimate" and line["quote"] is None and line["unit_cost"] == vehicle["unit_cost"]


def test_quote_on_extra_line_saves_to_rate_card_and_follows_new_version(planner_client, itinerary, admin_client):
    iid = itinerary["id"]
    guide = admin_client.post(f"{API}/inventory/suppliers", json={"name": f"Paris Guides {_uid()}", "supplier_type": "guide"}).json()
    p = planner_client.post(f"{API}/itineraries/{iid}/pricing/lines", json={"category": "guide", "basis": "per_day", "description": "Paris guide", "quantity": "2"}).json()
    key = next(l["key"] for l in p["lines"] if l["manual_id"])
    q = planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={
        "key": key, "supplier_id": guide["id"], "amount": "280", "currency": "EUR", "status": "confirmed", "reference": "WhatsApp", "save_as_rate": True,
        "service": "Licensed guide, full day"}).json()
    line = next(l for l in q["lines"] if l["key"] == key)
    assert line["unit_cost"] == "280.00" and line["status"] == "confirmed" and line["supplier_name"] == guide["name"] and line["total"] == "560.00"
    card = planner_client.get(f"{API}/suppliers/{guide['id']}/rates").json()
    assert [(r["service"], D(r["unit_cost"]), r["basis"]) for r in card] == [("Licensed guide, full day", D(280), "per_day")]

    planner_client.post(f"{API}/itineraries/{iid}/edit")  # new working version keeps the quotes
    p2 = planner_client.get(f"{API}/itineraries/{iid}/pricing").json()
    assert p2["version_number"] == 2
    copied = next(l for l in p2["lines"] if l["manual_id"])
    assert copied["status"] == "confirmed" and copied["quote"]["reference"] == "WhatsApp"

    cleared = planner_client.delete(f"{API}/itineraries/{iid}/pricing/quote", params={"key": copied["key"]}).json()
    assert next(l for l in cleared["lines"] if l["key"] == copied["key"])["status"] == "estimate"
    assert planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={"key": "manual:999999", "amount": "1"}).status_code == 404
    assert planner_client.put(f"{API}/itineraries/{iid}/pricing/quote", json={"key": "nope", "amount": "1"}).status_code == 404
