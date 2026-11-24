"""Visual itinerary builder (PRD Part 14 + Part 25 cases 11-14, 16-17)."""

import pytest

from tests.test_itineraries import API, _requirements, enquiry, world  # noqa: F401  (fixtures)


@pytest.fixture()
def itinerary(planner_client, enquiry, world):  # noqa: F811
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world))
    plans = planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()
    return plans[0]


def _consistent(d):
    assert [x["day_number"] for x in d["days"]] == list(range(1, d["total_days"] + 1))
    assert d["total_nights"] == d["total_days"] - 1
    assert sum(s["nights"] for s in d["stays"]) == d["total_nights"]
    assert sum(r["nights"] for r in d["route"]) == d["total_nights"]
    assert d["days"][-1]["overnight_city"] is None


def test_generated_version_is_read_only_until_editing(planner_client, itinerary):
    it = itinerary
    d = planner_client.get(f"{API}/itineraries/{it['id']}").json()
    assert d["is_locked"] and d["version_number"] == 1
    r = planner_client.post(f"{API}/itineraries/{it['id']}/days/2/add-after")
    assert r.status_code == 409 and r.json()["error"] == "version_locked"
    w = planner_client.post(f"{API}/itineraries/{it['id']}/edit").json()
    assert w["version_number"] == 2 and not w["is_locked"] and w["version_label"] == "Working draft"
    again = planner_client.post(f"{API}/itineraries/{it['id']}/edit").json()
    assert again["version_number"] == 2  # idempotent while a draft exists


def test_case_13_14_add_and_remove_day_keep_everything_consistent(planner_client, itinerary):
    iid = itinerary["id"]
    base = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    added = planner_client.post(f"{API}/itineraries/{iid}/days/3/add-after").json()
    assert added["total_days"] == base["total_days"] + 1
    _consistent(added)
    assert added["days"][3]["activities"][0]["title"] == "Free day"
    city = added["days"][2]["overnight_city"]
    assert next(s for s in added["route"] if s["city"] == city)["nights"] == next(s for s in base["route"] if s["city"] == city)["nights"] + 1

    dup = planner_client.post(f"{API}/itineraries/{iid}/days/2/duplicate").json()
    assert dup["total_days"] == base["total_days"] + 2
    _consistent(dup)

    removed = planner_client.delete(f"{API}/itineraries/{iid}/days/4").json()
    assert removed["total_days"] == base["total_days"] + 1
    _consistent(removed)
    assert planner_client.delete(f"{API}/itineraries/{iid}/days/1").status_code == 400  # arrival day
    last = removed["total_days"]
    assert planner_client.delete(f"{API}/itineraries/{iid}/days/{last}").status_code == 400  # departure day
    assert planner_client.post(f"{API}/itineraries/{iid}/days/{last}/add-after").status_code == 400


def test_removing_all_nights_in_a_city_rebuilds_route_and_legs(planner_client, itinerary):
    iid = itinerary["id"]
    d = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    first_city = d["days"][0]["overnight_city"]
    second_stay = d["stays"][1]
    for _ in range(second_stay["nights"]):
        d = planner_client.delete(f"{API}/itineraries/{iid}/days/{second_stay['check_in_day']}").json()
    _consistent(d)
    assert second_stay["city"] not in [s["city"] for s in d["route"]]
    legs = [t for t in d["transports"] if t["kind"] == "intercity"]
    assert legs[0]["from_city"] == first_city and legs[0]["to_city"] == d["route"][1]["city"]


def test_case_12_activities_add_move_edit_remove(planner_client, admin_client, itinerary, world):
    iid = itinerary["id"]
    d = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    paris_day = next(x for x in d["days"] if x["city"] == world["par"]["name"] and x["overnight_city"] and x["day_number"] > 1)
    att = admin_client.post(f"{API}/inventory/attractions", json={"city_id": world["par"]["id"], "name": "Extra gallery", "category": "museum",
                                                                  "recommended_duration_min": 90}).json()
    d = planner_client.post(f"{API}/itineraries/{iid}/days/{paris_day['day_number']}/activities",
                            json={"time_slot": "afternoon", "attraction_id": att["id"]}).json()
    day = next(x for x in d["days"] if x["day_number"] == paris_day["day_number"])
    new = next(a for a in day["activities"] if a["attraction_id"] == att["id"])
    assert new["title"] == "Extra gallery" and new["duration_min"] == 90

    d = planner_client.post(f"{API}/itineraries/{iid}/activities/{new['id']}/move", json={"day_number": paris_day["day_number"], "position": 0, "time_slot": "morning"}).json()
    day = next(x for x in d["days"] if x["day_number"] == paris_day["day_number"])
    assert day["activities"][0]["id"] == new["id"] and day["activities"][0]["time_slot"] == "morning"

    d = planner_client.patch(f"{API}/itineraries/{iid}/activities/{new['id']}", json={"title": "Private gallery tour", "description": "With guide"}).json()
    assert any(a["title"] == "Private gallery tour" for x in d["days"] for a in x["activities"])

    d = planner_client.post(f"{API}/itineraries/{iid}/days/{paris_day['day_number']}/activities",
                            json={"time_slot": "evening", "activity_type": "free_time", "title": "Seine evening walk"}).json()
    assert any(a["title"] == "Seine evening walk" for x in d["days"] for a in x["activities"])

    d = planner_client.delete(f"{API}/itineraries/{iid}/activities/{new['id']}").json()
    assert not any(a["id"] == new["id"] for x in d["days"] for a in x["activities"])


def test_live_checks_flag_duplicates_wrong_city_and_dietary(planner_client, admin_client, itinerary, world):
    iid = itinerary["id"]
    d = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    sight = next(a for x in d["days"] for a in x["activities"] if a["attraction_id"])
    other_day = next(x for x in d["days"] if x["overnight_city"] and not any(a["id"] == sight["id"] for a in x["activities"]))
    d = planner_client.post(f"{API}/itineraries/{iid}/days/{other_day['day_number']}/activities",
                            json={"time_slot": "morning", "attraction_id": sight["attraction_id"]}).json()
    assert any("again on day" in w for w in d["warnings"])
    # a non-vegetarian restaurant for an Indian vegetarian group is flagged
    steak = admin_client.post(f"{API}/inventory/restaurants", json={"city_id": world["ams"]["id"], "name": "Steak House", "vegetarian": False}).json()
    d = planner_client.put(f"{API}/itineraries/{iid}/days/2/meals/dinner", json={"arrangement": "restaurant", "restaurant_id": steak["id"]}).json()
    assert any("Steak House has no verified Indian vegetarian option" in w for w in d["warnings"])


def test_case_11_replace_hotel_and_transport(planner_client, admin_client, itinerary, world):
    iid = itinerary["id"]
    d = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    paris = next(s for s in d["stays"] if s["city"] == world["par"]["name"])
    five = world["hotels"][(world["par"]["id"], 5)]
    d = planner_client.put(f"{API}/itineraries/{iid}/stays/{paris['id']}/hotel", json={"hotel_id": five["id"]}).json()
    paris2 = next(s for s in d["stays"] if s["city"] == world["par"]["name"])
    assert paris2["hotel"]["id"] == five["id"] and paris2["estimated_cost"]
    assert paris["hotel"]["id"] in [h["id"] for h in paris2["alternatives"]]  # previous choice kept as an alternative
    wrong_city = world["hotels"][(world["ams"]["id"], 4)]
    assert planner_client.put(f"{API}/itineraries/{iid}/stays/{paris2['id']}/hotel", json={"hotel_id": wrong_city["id"]}).status_code == 400

    leg = next(t for t in d["transports"] if t["kind"] == "intercity")
    d = planner_client.patch(f"{API}/itineraries/{iid}/transports/{leg['id']}", json={"mode": "train"}).json()
    assert next(t for t in d["transports"] if t["id"] == leg["id"])["mode"] == "train"
    assert any(c["description"].startswith("Train") and c["amount"] is None for c in d["costs"])
    d = planner_client.put(f"{API}/itineraries/{iid}/vehicle", json={"vehicle_id": None}).json()
    assert "No vehicle assigned." in d["warnings"]


def test_case_16_17_save_version_restore_and_compare(planner_client, itinerary):
    iid = itinerary["id"]
    planner_client.post(f"{API}/itineraries/{iid}/edit")
    planner_client.post(f"{API}/itineraries/{iid}/days/3/add-after")
    saved = planner_client.post(f"{API}/itineraries/{iid}/versions", json={"label": "Additional day", "notes": "Agent asked"}).json()
    assert saved["is_locked"] and saved["version_label"] == "Additional day" and saved["version_number"] == 2
    assert planner_client.post(f"{API}/itineraries/{iid}/days/2/add-after").status_code == 409  # saved = read-only

    diff = planner_client.get(f"{API}/itineraries/{iid}/versions/compare", params={"a": 1, "b": 2}).json()
    assert any("Trip length: 10 → 11 days (+1)" in s for s in diff["summary"])

    restored = planner_client.post(f"{API}/itineraries/{iid}/versions/1/restore").json()
    assert restored["version_number"] == 3 and not restored["is_locked"] and restored["total_days"] == 10
    versions = planner_client.get(f"{API}/itineraries/{iid}/versions").json()
    assert [v["version_number"] for v in versions] == [3, 2, 1]
    assert planner_client.get(f"{API}/itineraries/{iid}", params={"version": 2}).json()["total_days"] == 11  # earlier versions preserved

    # restoring while a draft is open keeps the draft (auto-saved), nothing is lost
    planner_client.post(f"{API}/itineraries/{iid}/days/2/add-after")
    planner_client.post(f"{API}/itineraries/{iid}/versions/2/restore")
    versions = planner_client.get(f"{API}/itineraries/{iid}/versions").json()
    assert versions[1]["version_number"] == 3 and versions[1]["is_locked"] and "auto-saved" in versions[1]["label"]


def test_duplicate_itinerary(planner_client, itinerary):
    copy = planner_client.post(f"{API}/itineraries/{itinerary['id']}/duplicate").json()
    assert copy["id"] != itinerary["id"] and copy["version_number"] == 1 and not copy["is_locked"]
    assert copy["total_days"] == itinerary["total_days"]
