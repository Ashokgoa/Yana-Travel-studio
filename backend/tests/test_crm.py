import uuid
from datetime import date

import pytest


def _agent(c, **overrides):
    body = {"company_name": f"Agency {uuid.uuid4().hex[:6]}", "contact_person": "Priya", "email": "a@agency.example.com",
            "phone": "+91 99999", "country": "India", **overrides}
    r = c.post("/api/v1/travel-agents", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _customer(c, agent_id, **overrides):
    body = {"travel_agent_id": agent_id, "name": f"Customer {uuid.uuid4().hex[:6]}", "adults": 4, "children": 2,
            "children_ages": [8, 11], **overrides}
    r = c.post("/api/v1/customers", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _enquiry(c, agent_id, customer_id, **overrides):
    body = {"travel_agent_id": agent_id, "customer_id": customer_id, "enquiry_date": "2026-11-23",
            "travel_start_date": "2027-06-01", "travel_end_date": "2027-06-15", "adults": 4, "children": 2,
            "destination_preferences": "Amsterdam, Paris, Switzerland", "budget_amount": "3000",
            "budget_currency": "eur", "budget_basis": "per_person", **overrides}
    r = c.post("/api/v1/enquiries", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ travel agents
def test_agent_crud_search_and_filter(planner_client):
    a = _agent(planner_client, company_name="Sunrise Holidays Zeta", country="India")
    _agent(planner_client, company_name="Other Tours", country="UAE")

    got = planner_client.get(f"/api/v1/travel-agents/{a['id']}").json()
    assert got["company_name"] == "Sunrise Holidays Zeta" and got["status"] == "active"

    found = planner_client.get("/api/v1/travel-agents", params={"q": "sunrise holidays z"}).json()
    assert [x["id"] for x in found["items"]] == [a["id"]]

    by_country = planner_client.get("/api/v1/travel-agents", params={"country": "uae"}).json()
    assert all(x["country"] == "UAE" for x in by_country["items"]) and by_country["total"] >= 1

    updated = planner_client.put(f"/api/v1/travel-agents/{a['id']}", json={**got, "phone": "", "internal_notes": "VIP"}).json()
    assert updated["phone"] is None and updated["internal_notes"] == "VIP"


def test_agent_deactivate_and_status_filter(planner_client):
    a = _agent(planner_client)
    r = planner_client.patch(f"/api/v1/travel-agents/{a['id']}/status", json={"status": "inactive"})
    assert r.json()["status"] == "inactive"
    inactive = planner_client.get("/api/v1/travel-agents", params={"status": "inactive", "page_size": 100}).json()
    assert a["id"] in [x["id"] for x in inactive["items"]]


def test_agent_validation(planner_client):
    r = planner_client.post("/api/v1/travel-agents", json={"company_name": "  ", "email": "not-an-email"})
    assert r.status_code == 422
    fields = {d["field"] for d in r.json()["details"]}
    assert {"company_name", "email"} <= fields


def test_search_treats_wildcards_literally(planner_client):
    _agent(planner_client, company_name="100% Travel")
    r = planner_client.get("/api/v1/travel-agents", params={"q": "%", "page_size": 100}).json()
    assert all("%" in x["company_name"] for x in r["items"])


def test_pagination(planner_client):
    for _ in range(3):
        _agent(planner_client, country="Pagination-Land")
    page1 = planner_client.get("/api/v1/travel-agents", params={"country": "Pagination-Land", "page_size": 2}).json()
    page2 = planner_client.get("/api/v1/travel-agents", params={"country": "Pagination-Land", "page_size": 2, "page": 2}).json()
    assert page1["total"] == 3 and len(page1["items"]) == 2 and len(page2["items"]) == 1


# ------------------------------------------------------------------ customers
def test_customer_linked_to_agent_with_counts(planner_client):
    a = _agent(planner_client)
    c = _customer(planner_client, a["id"])
    assert c["travel_agent"]["id"] == a["id"] and c["children_ages"] == [8, 11]
    assert planner_client.get(f"/api/v1/travel-agents/{a['id']}").json()["customer_count"] == 1
    listed = planner_client.get("/api/v1/customers", params={"travel_agent_id": a["id"]}).json()
    assert [x["id"] for x in listed["items"]] == [c["id"]]


@pytest.mark.parametrize("payload, message", [
    ({"children": 2, "children_ages": [5]}, "age for each child"),
    ({"children": 1, "children_ages": [19]}, "between 0 and 17"),
    ({"adults": 0, "children": 0, "children_ages": []}, "At least one traveller"),
])
def test_customer_traveller_validation(planner_client, payload, message):
    r = planner_client.post("/api/v1/customers", json={"name": "X", **payload})
    assert r.status_code == 422 and message in r.json()["details"][0]["message"]


def test_customer_cannot_be_added_to_inactive_agent(planner_client):
    a = _agent(planner_client)
    planner_client.patch(f"/api/v1/travel-agents/{a['id']}/status", json={"status": "inactive"})
    r = planner_client.post("/api/v1/customers", json={"travel_agent_id": a["id"], "name": "X", "adults": 2})
    assert r.status_code == 400 and r.json()["error"] == "inactive_agent"


# ------------------------------------------------------------------ enquiries
def test_enquiry_reference_sequence_per_year(planner_client):
    a = _agent(planner_client)
    c = _customer(planner_client, a["id"])
    e1 = _enquiry(planner_client, a["id"], c["id"], enquiry_date="2031-01-05")
    e2 = _enquiry(planner_client, a["id"], c["id"], enquiry_date="2031-02-05")
    e3 = _enquiry(planner_client, a["id"], c["id"], enquiry_date="2032-01-01")
    assert (e1["reference"], e2["reference"], e3["reference"]) == ("ENQ-2031-0001", "ENQ-2031-0002", "ENQ-2032-0001")


def test_enquiry_created_as_new_with_history_and_normalised_currency(planner_client):
    a = _agent(planner_client)
    c = _customer(planner_client, a["id"])
    e = _enquiry(planner_client, a["id"], c["id"])
    assert e["status"] == "new" and e["budget_currency"] == "EUR" and e["total_travellers"] == 6
    assert [h["to_status"] for h in e["status_history"]] == ["new"]
    assert e["status_history"][0]["changed_by"]["full_name"] == "Test Planner"


def test_enquiry_status_change_recorded(planner_client):
    a = _agent(planner_client)
    c = _customer(planner_client, a["id"])
    e = _enquiry(planner_client, a["id"], c["id"])
    r = planner_client.post(f"/api/v1/enquiries/{e['id']}/status", json={"status": "in_progress", "note": "Started"})
    body = r.json()
    assert body["status"] == "in_progress"
    assert [(h["from_status"], h["to_status"]) for h in body["status_history"]] == [(None, "new"), ("new", "in_progress")]
    again = planner_client.post(f"/api/v1/enquiries/{e['id']}/status", json={"status": "in_progress"})
    assert again.status_code == 409


def test_enquiry_rejects_inconsistent_data(planner_client):
    a = _agent(planner_client)
    other = _agent(planner_client)
    c = _customer(planner_client, a["id"])

    r = planner_client.post("/api/v1/enquiries", json={"travel_agent_id": other["id"], "customer_id": c["id"], "adults": 2})
    assert r.status_code == 400 and r.json()["error"] == "customer_agent_mismatch"

    r = planner_client.post("/api/v1/enquiries", json={"travel_agent_id": a["id"], "customer_id": c["id"], "adults": 2,
                                                         "travel_start_date": "2027-06-10", "travel_end_date": "2027-06-01"})
    assert r.status_code == 422 and "end date" in r.json()["details"][0]["message"]

    r = planner_client.post("/api/v1/enquiries", json={"travel_agent_id": a["id"], "customer_id": c["id"], "adults": 2, "budget_amount": 1000})
    assert r.status_code == 422 and "per person" in r.json()["details"][0]["message"]

    r = planner_client.post("/api/v1/enquiries", json={"travel_agent_id": a["id"], "customer_id": 999999, "adults": 2})
    assert r.status_code == 400


def test_enquiry_search_filter_and_assignment(planner_client, admin_client):
    a = _agent(planner_client, company_name="Filterable Voyages")
    c = _customer(planner_client, a["id"], name="Mehta Family Filter")
    planner_id = planner_client.get("/api/v1/auth/me").json()["id"]
    e = _enquiry(planner_client, a["id"], c["id"], assigned_planner_id=planner_id)
    assert e["assigned_planner"]["id"] == planner_id

    found = admin_client.get("/api/v1/enquiries", params={"q": "mehta family filter"}).json()
    assert [x["id"] for x in found["items"]] == [e["id"]]
    mine = admin_client.get("/api/v1/enquiries", params={"assigned_planner_id": planner_id, "status": "new", "page_size": 100}).json()
    assert e["id"] in [x["id"] for x in mine["items"]]
    assignable = admin_client.get("/api/v1/users/assignable").json()
    assert planner_id in [u["id"] for u in assignable]


def test_enquiry_update_keeps_reference(planner_client):
    a = _agent(planner_client)
    c = _customer(planner_client, a["id"])
    e = _enquiry(planner_client, a["id"], c["id"])
    body = {k: e[k] for k in ("travel_agent_id", "customer_id", "enquiry_date", "travel_start_date", "travel_end_date",
                              "adults", "children", "budget_amount", "budget_currency", "budget_basis")}
    r = planner_client.put(f"/api/v1/enquiries/{e['id']}", json={**body, "internal_comments": "Call agent Monday"})
    assert r.status_code == 200
    assert r.json()["reference"] == e["reference"] and r.json()["internal_comments"] == "Call agent Monday"


def test_dashboard_summary_counts(planner_client):
    before = planner_client.get("/api/v1/dashboard/summary").json()
    a = _agent(planner_client)
    c = _customer(planner_client, a["id"])
    e = _enquiry(planner_client, a["id"], c["id"], enquiry_date=date.today().isoformat())
    after = planner_client.get("/api/v1/dashboard/summary").json()
    assert after["total_enquiries"] == before["total_enquiries"] + 1
    assert after["by_status"]["new"] == before["by_status"]["new"] + 1
    assert set(after["by_status"]) == {"new", "in_progress", "proposal_generated", "sent_to_agent",
                                        "revision_requested", "approved", "booking_confirmed", "cancelled"}
    assert after["recent_enquiries"][0]["id"] == e["id"]
