"""Day-by-day planning by hand, PDF day texts and photos, templates with PDF design, template import (Phase 8d)."""

import re

import pytest

from tests.test_itineraries import API, _requirements, _uid, enquiry, world  # noqa: F401  (fixtures)
from tests.test_media import make_image, upload


@pytest.fixture()
def planned(planner_client, enquiry, world):  # noqa: F811
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world))
    r = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/blank", json={"city_id": world["ams"]["id"], "title": "Family tour"})
    assert r.status_code == 201, r.text
    return r.json()


def _day(it, n):
    return next(d for d in it["days"] if d["day_number"] == n)


def _patch_day(c, iid, n, **body):
    r = c.patch(f"{API}/itineraries/{iid}/days/{n}", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_blank_itinerary_from_enquiry_dates(planned, world):
    it = planned
    assert it["strategy"] == "custom" and not it["is_locked"] and it["version_label"] == "Draft" and it["title"] == "Family tour"
    assert it["start_date"] == "2027-06-01" and it["total_days"] == 10 and it["total_nights"] == 9
    assert all(d["city"] == world["ams"]["name"] for d in it["days"])
    assert _day(it, 10)["overnight_city"] is None
    assert [(s["city"], s["nights"], s["hotel"]) for s in it["stays"]] == [(world["ams"]["name"], 9, None)]
    assert any("No hotel selected" in w for w in it["warnings"])
    assert _day(it, 1)["activities"][0]["activity_type"] == "arrival" and _day(it, 10)["activities"][-1]["activity_type"] == "departure"


def test_plan_cities_day_by_day_updates_stays_legs_and_moves(planner_client, planned, world):
    iid = planned["id"]
    par, luc, zrh = world["par"], world["luc"], world["zrh"]
    for n in range(4, 8):
        it = _patch_day(planner_client, iid, n, city_id=par["id"], overnight_city_id=par["id"])
    for n in range(8, 10):
        it = _patch_day(planner_client, iid, n, city_id=luc["id"], overnight_city_id=luc["id"])
    it = _patch_day(planner_client, iid, 10, city_id=zrh["id"], overnight_city_id=zrh["id"])  # departure day: overnight ignored
    assert [(s["city"], s["check_in_day"], s["nights"]) for s in it["stays"]] == [
        (world["ams"]["name"], 1, 3), (par["name"], 4, 4), (luc["name"], 8, 2)]
    legs = [(t["day_number"], t["from_city"], t["to_city"]) for t in it["transports"] if t["kind"] == "intercity"]
    assert legs == [(4, world["ams"]["name"], par["name"]), (8, par["name"], luc["name"])]
    assert _day(it, 4)["title"] == f"{world['ams']['name']} → {par['name']}" and _day(it, 5)["title"] == par["name"]
    d4 = [a["activity_type"] for a in _day(it, 4)["activities"]]
    assert d4[0] == "check_out" and "transfer" in d4 and d4[-1] == "check_in"
    assert [a["activity_type"] for a in _day(it, 5)["activities"]].count("check_in") == 0
    assert _day(it, 10)["overnight_city"] is None and _day(it, 10)["activities"][0]["activity_type"] == "check_out"
    departure = next(t for t in it["transports"] if t["kind"] == "airport_transfer" and t["to_city"] is None)
    assert departure["from_city"] == luc["name"]
    # Choose a hotel for the new Paris stay (planner's choice).
    stay = next(s for s in it["stays"] if s["city"] == par["name"])
    hotel = world["hotels"][(par["id"], 4)]
    it = planner_client.put(f"{API}/itineraries/{iid}/stays/{stay['id']}/hotel", json={"hotel_id": hotel["id"]}).json()
    assert next(s for s in it["stays"] if s["city"] == par["name"])["hotel"]["id"] == hotel["id"]
    assert planner_client.patch(f"{API}/itineraries/{iid}/days/3", json={"city_id": 999999}).status_code == 400
    assert planner_client.patch(f"{API}/itineraries/{iid}/days/3", json={"overnight_city_id": None}).status_code == 400
    assert planner_client.post(f"{API}/enquiries/999999/itineraries/blank", json={"city_id": par["id"]}).status_code == 404


def test_pdf_day_texts_and_cover_photo(planner_client, admin_client, planned):
    iid = planned["id"]
    opts = planner_client.get(f"{API}/itineraries/{iid}/proposal/options").json()
    days = opts["defaults"]["days"]
    assert len(days) == 10 and days[0]["heading"] and isinstance(days[0]["bullets"], list)
    cover = upload(admin_client, make_image(size=(1600, 900)), "cover.jpg").json()["media"]["id"]
    html = planner_client.post(f"{API}/itineraries/{iid}/proposal/preview", json={
        "cover_image": cover,
        "day_texts": {"2": {"heading": "Discover the Netherlands", "subtitle": "Windmills & canals",
                            "bullets": ["Visit **Zaanse Schans** by coach.", "", "Canal cruise in the evening."], "meals": "Breakfast and Indian dinner.",
                            "note": "Bring a light jacket."}},
    }).text
    assert "Day 2 · Discover the Netherlands" in html and "Windmills &amp; canals" in html
    assert "Visit <strong>Zaanse Schans</strong> by coach." in html and "Canal cruise in the evening." in html
    assert "Breakfast and Indian dinner." in html and "Bring a light jacket." in html
    assert 'class="cover-photo"' in html
    assert planner_client.put(f"{API}/itineraries/{iid}/proposal/settings", json={"cover_image": 999999}).status_code == 400


def test_templates_keep_their_pdf_texts(planner_client, planned, world):
    iid = planned["id"]
    planner_client.put(f"{API}/itineraries/{iid}/proposal/settings", json={"title": "Dutch Delights", "day_texts": {"1": {"heading": "Welkom!"}}})
    tpl = planner_client.post(f"{API}/itineraries/{iid}/save-as-template", json={"title": f"Dutch {_uid()}"}).json()
    agent = planner_client.post(f"{API}/travel-agents", json={"company_name": f"Tpl {_uid()}"}).json()
    cust = planner_client.post(f"{API}/customers", json={"travel_agent_id": agent["id"], "name": "Tpl Family", "adults": 2}).json()
    enq = planner_client.post(f"{API}/enquiries", json={"travel_agent_id": agent["id"], "customer_id": cust["id"], "adults": 2}).json()
    new = planner_client.post(f"{API}/enquiries/{enq['id']}/itineraries/from-template", json={"template_id": tpl["id"]}).json()
    s = planner_client.get(f"{API}/itineraries/{new['id']}/proposal/settings").json()
    assert s["title"] == "Dutch Delights" and s["day_texts"]["1"]["heading"] == "Welkom!"


def test_import_template_keeps_cities_on_the_way(db_session, world):
    from app.models import User
    from app.services.proposal_service import ProposalService
    from app.services.template_import import TemplatePlan, import_template

    user = db_session.query(User).first()
    via = f"Viaville {_uid()}"
    plan = TemplatePlan.model_validate({
        "title": "Imported tour", "start_date": "2027-05-01", "rooms": [{"label": "Double", "count": 2}],
        "create_cities": [{"name": via, "country": world["fr"]["iso_code"], "lat": 50.5, "lng": 3.5}],
        "create_attractions": [{"city": via, "name": "Via castle"}],
        "days": [
            {"city": world["ams"]["name"], "overnight": world["ams"]["name"], "title": "Arrival", "meals": {"dinner": "restaurant"}},
            {"city": via, "overnight": world["par"]["name"], "title": "On the way", "activities": [{"attraction": "Via castle"}]},
            {"city": world["par"]["name"], "overnight": world["par"]["name"], "title": "Paris", "activities": [{"attraction": "Iron tower"}, {"custom": "Boat"}]},
            {"city": world["luc"]["name"], "overnight": world["par"]["name"], "title": "Excursion", "activities": [{"attraction": "Glacier mountain"}]},
            {"city": world["par"]["name"], "overnight": None, "title": "Departure"},
        ],
        "pdf": {"title": "Imported", "day_texts": {"2": {"bullets": ["Stop at **Via castle**."]}}},
    })
    it, notes = import_template(db_session, user, plan)
    assert any("Added city" in n for n in notes)
    from app.services import itinerary_presenter as present
    d = present.detail(db_session, it)
    assert [x.city for x in d.days][:2] == [world["ams"]["name"], via]
    assert [(s.city, s.nights) for s in d.stays] == [(world["ams"]["name"], 1), (world["par"]["name"], 3)]
    assert [(t.from_city, t.to_city) for t in d.transports if t.kind == "intercity"] == [(world["ams"]["name"], via), (via, world["par"]["name"])]
    html = ProposalService(db_session).preview_html(it.id)
    route = re.search(r"Proposed Travel Route</h3>\s*<p>(.*?)</p>", html, re.S).group(1)
    assert via in route and world["luc"]["name"] not in route  # cities on the way yes, day excursions no
    assert "Stop at <strong>Via castle</strong>." in html


def test_changing_the_day_city_moves_the_night_too_unless_they_differ(planner_client, planned, world):
    iid = planned["id"]
    par, luc = world["par"], world["luc"]
    it = _patch_day(planner_client, iid, 5, city_id=par["id"])  # day and night were both Amsterdam: both move
    assert (_day(it, 5)["city"], _day(it, 5)["overnight_city"]) == (par["name"], par["name"])
    assert _day(it, 5)["title"] == f"{world['ams']['name']} → {par['name']}"  # automatic title follows: travel day
    it = _patch_day(planner_client, iid, 6, city_id=par["id"])
    it = _patch_day(planner_client, iid, 7, city_id=par["id"], overnight_city_id=par["id"])
    it = _patch_day(planner_client, iid, 6, city_id=luc["id"])  # day and night move together to Lucerne...
    assert _day(it, 6)["overnight_city"] == luc["name"]
    it = _patch_day(planner_client, iid, 6, overnight_city_id=par["id"])  # ...then sleep in Paris: a day trip
    assert (_day(it, 6)["city"], _day(it, 6)["overnight_city"]) == (luc["name"], par["name"])
    assert [(s["city"], s["nights"]) for s in it["stays"]] == [(world["ams"]["name"], 4), (par["name"], 3), (world["ams"]["name"], 2)]
