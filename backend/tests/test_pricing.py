"""Pricing & costing API (Phase 7) and its use in proposals."""

import math
import re
from decimal import Decimal as D

import pytest

from tests.test_itineraries import API, _requirements, enquiry, world  # noqa: F401  (fixtures)


@pytest.fixture()
def itinerary(planner_client, enquiry, world):  # noqa: F811
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world))
    return planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()[0]


def _p(c, iid):
    r = c.get(f"{API}/itineraries/{iid}/pricing")
    assert r.status_code == 200, r.text
    return r.json()


def _patch(c, iid, **body):
    r = c.patch(f"{API}/itineraries/{iid}/pricing", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _line_total(line, pax):
    return D(line["total"]) if line["total"] is not None else D(0)


def test_sheet_created_from_defaults_with_automatic_lines(planner_client, itinerary):
    p = _p(planner_client, itinerary["id"])
    assert p["version_number"] == 1 and p["currency"] == "EUR"
    assert set(p["margins"]) == {"hotel", "transport", "transfer", "sightseeing", "guide", "meal", "other"}
    assert all(D(m) == 15 for m in p["margins"].values())
    assert p["adults"] == 4 and p["children_with_bed"] == 2 and p["children_without_bed"] == 0 and p["singles"] == 0
    hotel_lines = [l for l in p["lines"] if l["category"] == "hotel"]
    assert hotel_lines and all(l["basis"] == "per_room" for l in hotel_lines)
    assert any("Family room" in l["description"] for l in hotel_lines) and any("Double" in l["description"] for l in hotel_lines)
    assert p["stays"] and all(D(s["double_rate"]) == 150 for s in p["stays"])
    assert all(s["single_is_estimate"] and s["single_rate"] is None for s in p["stays"])  # no single room type in this world
    assert any("double room rate is used for single use" in w for w in p["warnings"])
    # Actual cost = sum of included line totals (per-person lines x 6 travellers).
    assert D(p["total_cost"]) == sum((D(l["total"]) for l in p["lines"] if l["included"] and l["total"] is not None), D(0))
    pr = p["prices"]
    assert D(pr["adult_twin"]) > D(p["adult_twin_cost"]) and pr["child_with_bed"] == pr["adult_twin"]  # 100% bed share by default
    assert D(p["revenue"]) == 4 * D(pr["adult_twin"]) + 2 * D(pr["child_with_bed"])
    assert D(p["profit"]) == D(p["revenue"]) - D(p["total_cost"])


def test_prices_without_margin_equal_cost_and_child_bed_share(planner_client, itinerary):
    iid = itinerary["id"]
    p = _patch(planner_client, iid, margins={c: "0" for c in ("hotel", "transport", "transfer", "sightseeing", "guide", "meal", "other")}, rounding="0")
    assert D(p["prices"]["adult_twin"]) == D(p["adult_twin_cost"])
    twin_share = sum(D(s["double_rate"]) / 2 * s["nights"] for s in p["stays"])
    hotel = next(c for c in p["categories"] if c["category"] == "hotel")
    assert D(hotel["per_person_cost"]) == twin_share
    p = _patch(planner_client, iid, child_bed_pct="50", children_with_bed=1, children_without_bed=1)
    adult = D(p["prices"]["adult_twin"])
    assert D(p["prices"]["child_with_bed"]) == (adult - twin_share / 2).quantize(D("0.01"))
    assert D(p["prices"]["child_without_bed"]) == (adult - twin_share).quantize(D("0.01"))
    supplement = D(p["prices"]["single_supplement"])
    assert supplement == twin_share  # single = double rate (estimate) -> supplement = the other half


def test_margins_discount_rounding_and_currency(planner_client, itinerary):
    iid = itinerary["id"]
    base = _patch(planner_client, iid, margins={c: "0" for c in ("hotel", "transport", "transfer", "sightseeing", "guide", "meal", "other")}, rounding="0")
    cost = D(base["prices"]["adult_twin"])
    hotel_pp = D(next(c for c in base["categories"] if c["category"] == "hotel")["per_person_cost"])
    p = _patch(planner_client, iid, margins={"hotel": "10"})
    assert D(p["prices"]["adult_twin"]) == (cost + hotel_pp * D("0.10")).quantize(D("0.01"))
    p = _patch(planner_client, iid, discount_pct="5", adjustment_per_person="25", rounding="10")
    expected = math.ceil(((cost + hotel_pp * D("0.10")) * D("0.95") + 25) / 10) * 10
    assert D(p["prices"]["adult_twin"]) == expected
    p = _patch(planner_client, iid, display_currency="INR", exchange_rate="90.5", pdf_currency="both")
    assert p["display_prices"]["currency"] == "INR"
    assert D(p["display_prices"]["adult_twin"]) == math.ceil(D(p["prices"]["adult_twin"]) * D("90.5"))
    assert planner_client.patch(f"{API}/itineraries/{iid}/pricing", json={"margins": {"hotel": "400"}}).status_code == 422
    assert planner_client.patch(f"{API}/itineraries/{iid}/pricing", json={"margins": {"spa": "10"}}).status_code == 422
    assert planner_client.patch(f"{API}/itineraries/{iid}/pricing", json={"discount_pct": "120"}).status_code == 422


def test_overrides_manual_lines_and_stay_rates(planner_client, itinerary):
    iid = itinerary["id"]
    p = _patch(planner_client, iid, margins={"guide": "20"}, rounding="0")
    before_cost, before_adult = D(p["total_cost"]), D(p["prices"]["adult_twin"])
    hotel = next(l for l in p["lines"] if l["category"] == "hotel")

    o = planner_client.put(f"{API}/itineraries/{iid}/pricing/overrides", json={"key": hotel["key"], "unit_cost": "100"}).json()
    line = next(l for l in o["lines"] if l["key"] == hotel["key"])
    assert line["is_overridden"] and line["unit_cost"] == "100" and line["auto_unit_cost"] == hotel["unit_cost"] and not line["is_estimate"]
    assert D(o["total_cost"]) == before_cost - (D(hotel["unit_cost"]) - 100) * D(hotel["quantity"])
    o = planner_client.put(f"{API}/itineraries/{iid}/pricing/overrides", json={"key": hotel["key"], "included": False}).json()
    assert not next(l for l in o["lines"] if l["key"] == hotel["key"])["included"]
    o = planner_client.delete(f"{API}/itineraries/{iid}/pricing/overrides", params={"key": hotel["key"]}).json()
    assert D(o["total_cost"]) == before_cost

    r = planner_client.post(f"{API}/itineraries/{iid}/pricing/lines", json={"category": "guide", "basis": "per_day", "description": "Paris guide", "unit_cost": "200", "quantity": "3"})
    assert r.status_code == 201
    m = r.json()
    assert D(m["total_cost"]) == before_cost + 600
    assert D(m["prices"]["adult_twin"]) == (before_adult + D(600) / 6 * D("1.2")).quantize(D("0.01"))
    manual = next(l for l in m["lines"] if l["manual_id"])
    m = planner_client.put(f"{API}/itineraries/{iid}/pricing/lines/{manual['manual_id']}", json={"category": "guide", "basis": "group", "description": "Paris guide", "unit_cost": "300"}).json()
    assert D(m["total_cost"]) == before_cost + 300
    unpriced = planner_client.post(f"{API}/itineraries/{iid}/pricing/lines", json={"category": "other", "basis": "group", "description": "Tolls"}).json()
    assert "no price yet" in unpriced["warnings"][0]
    m = planner_client.delete(f"{API}/itineraries/{iid}/pricing/lines/{manual['manual_id']}").json()
    assert planner_client.delete(f"{API}/itineraries/{iid}/pricing/lines/999999").status_code == 404

    stay = p["stays"][0]
    s = planner_client.put(f"{API}/itineraries/{iid}/pricing/stay-rates", json={"key": stay["key"], "single_rate": "120"}).json()
    st = next(x for x in s["stays"] if x["key"] == stay["key"])
    assert st["single_rate"] == "120" and not st["single_is_estimate"] and st["is_overridden"]
    s = planner_client.put(f"{API}/itineraries/{iid}/pricing/stay-rates", json={"key": stay["key"]}).json()
    assert next(x for x in s["stays"] if x["key"] == stay["key"])["single_rate"] is None


def test_defaults_admin_only_and_pricing_follows_new_versions(planner_client, admin_client, itinerary):
    d = planner_client.get(f"{API}/settings/pricing").json()
    assert not d["margins_reviewed"]
    assert planner_client.put(f"{API}/settings/pricing", json=d).status_code == 403
    try:
        assert admin_client.put(f"{API}/settings/pricing", json={**d, "margins": {"hotel": "12", "transport": "20"}, "rounding": "5"}).status_code == 200
        iid = itinerary["id"]
        p = _p(planner_client, iid)
        assert D(p["margins"]["hotel"]) == 12 and D(p["margins"]["transport"]) == 20 and D(p["margins"]["meal"]) == 0
        assert D(p["prices"]["adult_twin"]) % 5 == 0
        planner_client.post(f"{API}/itineraries/{iid}/pricing/lines", json={"category": "guide", "basis": "group", "description": "Guide", "unit_cost": "250"})
        _patch(planner_client, iid, discount_pct="3")
        v2 = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
        assert v2["version_number"] == 2
        p2 = _p(planner_client, iid)
        assert p2["version_number"] == 2 and D(p2["discount_pct"]) == 3 and any(l["description"] == "Guide" for l in p2["lines"])
        assert planner_client.get(f"{API}/itineraries/{iid}/pricing", params={"version": 1}).json()["version_number"] == 1
    finally:
        admin_client.put(f"{API}/settings/pricing", json={})


def test_proposal_uses_selling_prices_never_costs(planner_client, itinerary):
    iid = itinerary["id"]
    html = planner_client.post(f"{API}/itineraries/{iid}/proposal/preview").text
    assert "Price on request" in html  # not priced yet
    assert planner_client.get(f"{API}/itineraries/{iid}/proposal/options").json()["pricing"]["status"] == "none"

    p = _patch(planner_client, iid, children_with_bed=1, children_without_bed=1, singles=1, rounding="10",
               display_currency="INR", exchange_rate="90", pdf_currency="both")
    html = planner_client.post(f"{API}/itineraries/{iid}/proposal/preview").text
    adult = f"EUR {D(p['prices']['adult_twin']):,.0f}"
    for text in ("Per adult, sharing a twin / double room", adult, "INR", "Single room supplement", "Per child with a bed", "Per child without a bed"):
        assert text in html, text
    visible = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|svg)\b.*?</\1>", "", html, flags=re.S))
    for secret in (p["total_cost"], p["profit"], p["adult_twin_cost"], p["revenue"]):
        amount = D(secret)
        assert f"{amount:,.0f}" not in visible and f"{amount:,.2f}" not in visible, secret
    assert "margin" not in visible.lower() and "profit" not in visible.lower()
    opts = planner_client.get(f"{API}/itineraries/{iid}/proposal/options").json()
    assert opts["pricing"]["status"] == "ok" and adult in opts["pricing"]["text"]

    # A price typed in the designer wins.
    html = planner_client.post(f"{API}/itineraries/{iid}/proposal/preview", json={"price_per_person": "2999"}).text
    assert "EUR 2,999" in html and "Per adult, sharing" not in html


def test_export_snapshot_keeps_the_price_shown(planner_client, itinerary, monkeypatch):
    class Fake:
        def render(self, html):
            return b"%PDF-1.7 fake"

    monkeypatch.setattr("app.services.proposal_service.get_pdf_renderer", lambda: Fake())
    iid = itinerary["id"]
    p = _patch(planner_client, iid, rounding="10")
    r = planner_client.post(f"{API}/itineraries/{iid}/proposal/export")
    assert r.status_code == 201
    from app.database.session import SessionLocal
    from app.models import ProposalExport

    with SessionLocal() as db:
        snap = db.get(ProposalExport, r.json()["id"]).settings["price_shown"]
    assert snap["rows"][0][1] == f"EUR {D(p['prices']['adult_twin']):,.0f}"
