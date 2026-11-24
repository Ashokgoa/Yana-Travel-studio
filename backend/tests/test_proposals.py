"""PDF proposals (Phase 6): route map, document content, settings, preview, export."""

import re

import pytest

from app.engines.route_map import MapStop, render_route_map
from app.services.proposal_content import flag_data_uri
from app.services.proposal_service import proposal_filename
from tests.test_itineraries import API, _requirements, enquiry, world  # noqa: F401  (fixtures)
from tests.test_media import make_image, upload


class FakeRenderer:
    def __init__(self):
        self.html = None

    def render(self, html: str) -> bytes:
        self.html = html
        return b"%PDF-1.7 fake " + str(len(html)).encode()


@pytest.fixture()
def fake_pdf(monkeypatch):
    renderer = FakeRenderer()
    monkeypatch.setattr("app.services.proposal_service.get_pdf_renderer", lambda: renderer)
    return renderer


@pytest.fixture()
def itinerary(planner_client, enquiry, world):  # noqa: F811
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world, travel_type="GIT"))
    return planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()[0]


def _preview(c, iid, **settings):
    r = c.post(f"{API}/itineraries/{iid}/proposal/preview", json=settings or None)
    assert r.status_code == 200, r.text
    return r


# ------------------------------------------------------------------ map (unit)
def test_route_map_draws_route_labels_legend_and_flags():
    stops = [MapStop("Amsterdam", "Netherlands", "NL", 52.37, 4.90), MapStop("Paris", "France", "FR", 48.86, 2.35),
             MapStop("Paris", "France", "FR", 48.86, 2.35), MapStop("Zurich", "Switzerland", "CH", 47.37, 8.54)]
    svg = render_route_map(stops, arrival_label="Arrival", departure_label="Departure", flag_for=flag_data_uri)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    for text in ("Amsterdam", "Paris", "Zurich", "Proposed Travel Route", "Arrival Amsterdam, Netherlands", "Departure", "FRANCE", " km"):
        assert text in svg
    assert svg.count("data:image/svg+xml;base64,") == 3  # one legend flag per city row (NL, FR, CH)
    assert svg.count("stroke-dasharray=\"9 7\"") == 1  # one dashed route path (duplicate Paris ignored)
    assert "http" not in svg.replace("http://www.w3.org/2000/svg", "")  # fully offline


def test_route_map_single_city_and_unknown_country():
    svg = render_route_map([MapStop("Somewhere", "Atlantis", "QQ", 46.0, 7.0)])
    assert "Somewhere" in svg and "Atlantis" in svg


def test_proposal_filename():
    assert proposal_filename("Classic Europe", "Gen Family", 3) == "YANA_Classic_Europe_Gen_Family_V3.pdf"
    assert proposal_filename("Zürich & Côte d'Azur!", None, 1) == "YANA_Zurich_Cote_d_Azur_V1.pdf"
    assert proposal_filename("", "", 2) == "YANA_Proposal_V2.pdf"
    long = proposal_filename("Classic Europe: Netherlands, Belgium, France, Germany", "Sharma Family", 1)
    assert long == "YANA_Classic_Europe_Netherlands_Belgium_Sharma_Family_V1.pdf"


# ------------------------------------------------------------------ settings
def test_settings_default_save_and_validation(planner_client, itinerary):
    iid = itinerary["id"]
    s = planner_client.get(f"{API}/itineraries/{iid}/proposal/settings").json()
    assert s["template"] == "signature" and s["branding"] == "agent"
    assert [x["key"] for x in s["sections"]][:4] == ["cover", "highlights", "route_map", "days"] and all(x["enabled"] for x in s["sections"])

    body = {"template": "premium", "branding": "both", "sections": [{"key": "days", "enabled": True}, {"key": "terms", "enabled": False},
                                                                   {"key": "days", "enabled": False}],
            "title": "Swiss & Paris Highlights", "price_per_person": "2950", "inclusions": [" Hotels ", ""]}
    saved = planner_client.put(f"{API}/itineraries/{iid}/proposal/settings", json=body).json()
    keys = [x["key"] for x in saved["sections"]]
    assert keys[0] == "days" and keys[1] == "terms" and len(keys) == len(set(keys)) == 10  # order kept, duplicates dropped, rest appended
    assert saved["inclusions"] == ["Hotels"]
    assert planner_client.get(f"{API}/itineraries/{iid}/proposal/settings").json()["title"] == "Swiss & Paris Highlights"

    assert planner_client.put(f"{API}/itineraries/{iid}/proposal/settings", json={"template": "fancy"}).status_code == 422
    assert planner_client.put(f"{API}/itineraries/{iid}/proposal/settings", json={"primary_color": "red"}).status_code == 422
    r = planner_client.put(f"{API}/itineraries/{iid}/proposal/settings", json={"day_images": {"1": 999999}})
    assert r.status_code == 400 and r.json()["error"] == "invalid_image"


# ------------------------------------------------------------------ preview content
def test_preview_follows_the_sample_structure(planner_client, itinerary, enquiry, world):  # noqa: F811
    iid = itinerary["id"]
    r = _preview(planner_client, iid, template="classic")
    assert "default-src 'none'" in r.headers["content-security-policy"]
    html = r.text
    agent = planner_client.get(f"{API}/travel-agents/{enquiry['travel_agent_id']}").json()["company_name"]
    assert f"Curated by {agent}" in html
    assert "<h1>Classic Europe</h1>" in html  # short brochure title
    for text in ("Classic Europe", "3 Countries · 10 Days · 9 Nights", "Tour Highlights", "Group size:</b> 6 travellers (4 adults, 2 children)",
                 "Group Inclusive Tour (GIT)", "Proposed Travel Route", "<svg", "Day 1 ·", "Meals:</b>", "Your Hotels",
                 "Your Journey at a Glance", "Price on request", "Inclusions", "Exclusions", "Terms and Conditions",
                 "International flights", "Version 1 · Generated"):
        assert text in html, text
    assert f"Arrival {world['ams']['name']}" in html and html.count('<article class="day') == 10
    assert "Check in at <strong>Hotel" in html  # hotel names in the day text by default


def test_preview_never_shows_costs_or_internal_data(planner_client, itinerary):
    iid = itinerary["id"]
    options = planner_client.get(f"{API}/itineraries/{iid}/proposal/options").json()
    assert options["internal_estimate_per_person"]  # shown to the planner in the designer only
    assert options["defaults"]["inclusions"] and options["defaults"]["intro"].startswith("Discover")
    assert options["version_number"] == 1 and options["version_is_locked"]
    html = re.sub(r"<style>.*?</style>", "", _preview(planner_client, iid).text, flags=re.S)  # visible content only
    estimate = options["internal_estimate_per_person"]
    assert not re.search(rf"\b{estimate}\b", html.replace(",", ""))
    for word in ("estimated cost", "supplier", "margin", "base_price", "unverified", "DEMO"):
        assert word.lower() not in html.lower(), word
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", "", html, flags=re.S))
    assert not re.search(r"150", text)  # room base price from inventory


def test_preview_settings_change_output(planner_client, itinerary):
    iid = itinerary["id"]
    html = _preview(planner_client, iid, template="explorer", branding="yana", title="Alpine Escape", intro="Hand-written intro.",
                    price_per_person="2950", price_note="Per person sharing a twin room", hotel_names_in_days=False,
                    inclusions=["Only this"], exclusions=["Nothing else"], closing="Bye!",
                    sections=[{"key": "hotels", "enabled": False}, {"key": "terms", "enabled": False}]).text
    for text in ("Alpine Escape", "Hand-written intro.", "EUR 2,950", "Per person sharing a twin room", "Only this", "Nothing else",
                 "Bye!", "Curated by YANA DMC", 'class="timeline"', "#0F5257"):
        assert text in html, text
    assert "Your Hotels" not in html and "Terms and Conditions" not in html and "Check in at <strong>" not in html
    # Section order follows the settings: hotels/terms moved to the front but disabled, the rest in default order.
    assert html.index("Tour Highlights") < html.index("Day 1 ·") < html.index("Tour Price")


def test_branding_defaults_admin_only_and_both_mode(planner_client, admin_client, itinerary, enquiry):  # noqa: F811
    b = planner_client.get(f"{API}/settings/branding").json()
    assert b["company_name"] == "YANA DMC" and not b["terms_reviewed"]
    assert planner_client.put(f"{API}/settings/branding", json=b).status_code == 403
    logo = upload(admin_client, make_image("PNG", (300, 120)), "logo.png", category="brand").json()
    b.update(contact_line="info@yana.example · +31 20 000 0000", logo_media_id=logo["media"]["id"], default_terms="Our own terms.")
    assert admin_client.put(f"{API}/settings/branding", json=b).status_code == 200
    try:
        html = _preview(planner_client, itinerary["id"], branding="both").text
        agent = planner_client.get(f"{API}/travel-agents/{enquiry['travel_agent_id']}").json()["company_name"]
        assert f"Curated by {agent} in partnership with YANA DMC" in html
        assert "info@yana.example" in html and "Our own terms." in html and "data:image/png;base64," in html
        assert admin_client.put(f"{API}/settings/branding", json={**b, "logo_media_id": 999999}).status_code == 400
    finally:
        admin_client.put(f"{API}/settings/branding", json={})  # back to defaults for other tests


def test_photos_are_embedded_and_can_be_overridden(planner_client, admin_client, itinerary, world):
    iid = itinerary["id"]
    d = planner_client.get(f"{API}/itineraries/{iid}").json()
    att_day = next(x for x in d["days"] if any(a["attraction_id"] for a in x["activities"]))
    att_id = next(a["attraction_id"] for a in att_day["activities"] if a["attraction_id"])
    up = upload(admin_client, make_image(size=(1600, 1000)), "sight.jpg", category="attraction", entity_type="attraction", entity_id=att_id).json()
    city_up = upload(admin_client, make_image(size=(900, 600)), "city.jpg", category="city", entity_type="city", entity_id=att_day["city_id"]).json()

    options = planner_client.get(f"{API}/itineraries/{iid}/proposal/options").json()
    day_opts = next(o for o in options["day_images"] if o["day_number"] == att_day["day_number"])
    assert [c["media_id"] for c in day_opts["choices"]][:2] == [up["media"]["id"], city_up["media"]["id"]]

    html = _preview(planner_client, iid, template="classic").text
    assert html.count("data:image/jpeg;base64,") >= 2  # day photo + round photo on the map
    hidden = _preview(planner_client, iid, template="classic", day_images={str(att_day["day_number"]): 0}).text
    assert hidden.count('class="photo"') < html.count('class="photo"')


# ------------------------------------------------------------------ export
def test_export_saves_draft_as_version_records_file_and_updates_enquiry(planner_client, itinerary, enquiry, fake_pdf):  # noqa: F811
    iid = itinerary["id"]
    planner_client.post(f"{API}/itineraries/{iid}/edit")  # open working draft v2
    r = planner_client.post(f"{API}/itineraries/{iid}/proposal/export", json={"title": "Family Alps", "template": "premium"})
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["version_number"] == 2 and e["filename"] == "YANA_Family_Alps_Gen_Family_V2.pdf" and e["template"] == "premium"
    assert e["created_by_name"] == "Test Planner" and e["size_bytes"] > 10
    assert "Family Alps" in fake_pdf.html and "Version 2 · PDF proposal" in fake_pdf.html

    v = planner_client.get(f"{API}/itineraries/{iid}").json()
    assert v["version_number"] == 2 and v["is_locked"] and v["version_label"] == "PDF proposal"  # draft saved, read-only now
    assert planner_client.get(f"{API}/itineraries/{iid}/proposal/settings").json()["title"] == "Family Alps"  # settings remembered

    enq = planner_client.get(f"{API}/enquiries/{enquiry['id']}").json()
    assert enq["status"] == "proposal_generated"

    f = planner_client.get(f"{API}/itineraries/{iid}/proposal/exports/{e['id']}/file")
    assert f.status_code == 200 and f.content.startswith(b"%PDF") and f.headers["content-type"] == "application/pdf"
    assert 'filename="YANA_Family_Alps_Gen_Family_V2.pdf"' in f.headers["content-disposition"]

    # Exporting an old version keeps it; a second export is listed first.
    r2 = planner_client.post(f"{API}/itineraries/{iid}/proposal/export?version=1")
    assert r2.status_code == 201 and r2.json()["version_number"] == 1
    hist = planner_client.get(f"{API}/itineraries/{iid}/proposal/exports").json()
    assert [h["version_number"] for h in hist] == [1, 2]
    assert planner_client.get(f"{API}/itineraries/{iid}/proposal/exports/{e['id'] + 10_000}/file").status_code == 404


def test_export_does_not_move_enquiry_backwards(planner_client, itinerary, enquiry, fake_pdf):  # noqa: F811
    planner_client.post(f"{API}/enquiries/{enquiry['id']}/status", json={"status": "approved"})
    assert planner_client.post(f"{API}/itineraries/{itinerary['id']}/proposal/export").status_code == 201
    assert planner_client.get(f"{API}/enquiries/{enquiry['id']}").json()["status"] == "approved"


# ------------------------------------------------------------------ real browser (skipped if Edge/Chrome missing)
def _browser_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            for channel in ("msedge", "chrome"):
                try:
                    p.chromium.launch(channel=channel).close()
                    return True
                except Exception:
                    continue
    except Exception:
        return False
    return False


@pytest.mark.skipif(not _browser_available(), reason="No Edge or Chrome available for PDF rendering")
def test_real_pdf_is_a4_with_page_numbers(planner_client, itinerary):
    r = planner_client.post(f"{API}/itineraries/{itinerary['id']}/proposal/export", json={"template": "classic"})
    assert r.status_code == 201, r.text
    pdf = planner_client.get(f"{API}/itineraries/{itinerary['id']}/proposal/exports/{r.json()['id']}/file").content
    assert pdf.startswith(b"%PDF")
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    assert pages >= 3
    box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)", pdf)
    assert box and round(float(box.group(1))) == 595 and round(float(box.group(2))) == 842  # A4 in points


def test_signature_brochure_layout(planner_client, admin_client, itinerary, world):
    """Default style: fonts embedded, photo cover, overview, one page per day with overnight and dining cards."""
    iid = itinerary["id"]
    d = planner_client.get(f"{API}/itineraries/{iid}").json()
    day = next(x for x in d["days"] if sum(1 for a in x["activities"] if a["attraction_id"]) >= 1 and x["overnight_city"])
    for a in [a for a in day["activities"] if a["attraction_id"]]:
        for k in range(2):
            upload(admin_client, make_image(size=(1200, 800)), f"s{a['attraction_id']}{k}.jpg", category="attraction", entity_type="attraction", entity_id=a["attraction_id"])
    html = _preview(planner_client, iid).text
    assert "@font-face{font-family:'Playfair Display'" in html and "font/woff2;base64," in html
    assert '<section class="cover">' in html and "Tour proposal" in html and "Trip overview" in html
    assert html.count('<section class="page day">') == d["total_days"]
    assert "Overnight" in html and "Dining" in html and "Where you’ll stay" in html and "Your journey day by day" in html
    assert 'class="gallery' in html  # extra photos of the day's sightseeing
    assert re.search(r'class="hero (l|m|s)"', html)
    visible = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|svg)\b.*?</\1>", "", html, flags=re.S))
    for word in ("supplier", "margin", "estimated cost"):
        assert word not in visible.lower()
