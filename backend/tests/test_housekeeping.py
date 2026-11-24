"""Housekeeping (Phase 8b): backups and restore, demo data removal, itinerary templates."""

import io
import json
import sqlite3
import zipfile

import pytest
from alembic import command

from app.core.config import Settings
from app.core.errors import DomainError
from app.services.backup_service import BackupService
from tests.conftest import alembic_config
from tests.test_itineraries import API, _requirements, _uid, enquiry, world  # noqa: F401  (fixtures)
from tests.test_media import make_image, upload


# ------------------------------------------------------------------ backups (API, live test database)
def test_backup_api_admin_only_and_zip_contents(admin_client, planner_client):
    upload(admin_client, make_image(), "backup-test.jpg")
    assert planner_client.post(f"{API}/admin/backups").status_code == 403
    r = admin_client.post(f"{API}/admin/backups")
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["valid"] and b["created_by"] == "admin@example.com" and b["files"] >= 1 and b["counts"]["media"] >= 1
    assert any(x["name"] == b["name"] for x in admin_client.get(f"{API}/admin/backups").json())
    d = admin_client.get(f"{API}/admin/backups/{b['name']}/download")
    assert d.status_code == 200 and d.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(d.content)) as z:
        names = z.namelist()
        assert "manifest.json" in names and "database/yana_studio.db" in names and any(n.startswith("uploads/") for n in names)
        assert json.loads(z.read("manifest.json"))["alembic_revision"]
    for bad in ("..%2F..%2Fsecret.zip", "other.zip", "yana_backup_x.txt"):
        assert admin_client.get(f"{API}/admin/backups/{bad}/download").status_code == 404
    assert admin_client.delete(f"{API}/admin/backups/{b['name']}").status_code == 204
    assert admin_client.get(f"{API}/admin/backups/{b['name']}/download").status_code == 404


# ------------------------------------------------------------------ restore (separate throwaway installation)
@pytest.fixture()
def install(tmp_path):
    url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    s = Settings(database_url=url, uploads_dir=tmp_path / "uploads", exports_dir=tmp_path / "exports", backups_dir=tmp_path / "backups",
                 secret_key="x" * 40, environment="test")
    (s.uploads_dir / "hotels").mkdir(parents=True)
    (s.uploads_dir / "hotels" / "a.jpg").write_bytes(b"original-image")
    return s, tmp_path / "app.db"


def _countries(db_path):
    con = sqlite3.connect(db_path)
    try:
        return [r[0] for r in con.execute("SELECT name FROM countries ORDER BY name")]
    finally:
        con.close()


def test_restore_brings_back_database_and_files_with_a_safety_backup(install):
    settings, db_path = install
    con = sqlite3.connect(db_path)
    con.execute("INSERT INTO countries (name, iso_code, sort_order, is_active) VALUES ('Before', 'BF', 0, 1)")
    con.commit()
    con.close()
    svc = BackupService(settings=settings)
    first = svc.create(created_by="test")

    con = sqlite3.connect(db_path)
    con.execute("INSERT INTO countries (name, iso_code, sort_order, is_active) VALUES ('After', 'AF', 0, 1)")
    con.commit()
    con.close()
    (settings.uploads_dir / "hotels" / "a.jpg").write_bytes(b"changed")
    (settings.uploads_dir / "hotels" / "new.jpg").write_bytes(b"new")

    result = svc.restore(settings.backups_dir / first["name"])
    assert _countries(db_path) == ["Before"]
    assert (settings.uploads_dir / "hotels" / "a.jpg").read_bytes() == b"original-image"
    assert not (settings.uploads_dir / "hotels" / "new.jpg").exists()
    assert result["safety_backup"] and "before-restore" in result["safety_backup"]
    # The safety backup holds the state from just before the restore.
    svc.restore(settings.backups_dir / result["safety_backup"])
    assert _countries(db_path) == ["After", "Before"]


def test_restore_rejects_invalid_zips(install, tmp_path):
    settings, _ = install
    svc = BackupService(settings=settings)
    plain = tmp_path / "plain.zip"
    with zipfile.ZipFile(plain, "w") as z:
        z.writestr("hello.txt", "x")
    with pytest.raises(DomainError, match="not a YANA backup"):
        svc.restore(plain)
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("manifest.json", "{}")
        z.writestr("database/yana_studio.db", "x")
        z.writestr("../escape.txt", "x")
    with pytest.raises(DomainError, match="unsafe"):
        svc.restore(evil)
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(broken, "w") as z:
        z.writestr("manifest.json", "{}")
        z.writestr("database/yana_studio.db", b"not a database" * 100)
    with pytest.raises(Exception):
        svc.restore(broken)


# ------------------------------------------------------------------ demo data
@pytest.fixture()
def itinerary(planner_client, enquiry, world):  # noqa: F811
    planner_client.put(f"{API}/enquiries/{enquiry['id']}/requirements", json=_requirements(world))
    return planner_client.post(f"{API}/enquiries/{enquiry['id']}/itineraries/generate", json={"strategies": ["classic"]}).json()[0]


def test_remove_demo_data_keeps_what_itineraries_use(admin_client, planner_client, itinerary, world):
    def demo_hotel(name):
        h = admin_client.post(f"{API}/inventory/hotels", json={"city_id": world["par"]["id"], "name": name, "star_rating": 4, "is_demo": True}).json()
        admin_client.post(f"{API}/inventory/hotels/{h['id']}/room-types", json={"name": "Double", "max_occupancy": 2, "base_price": "100"})
        return h

    unused, used = demo_hotel(f"Demo unused {_uid()}"), demo_hotel(f"Demo used {_uid()}")
    rest = admin_client.post(f"{API}/inventory/restaurants", json={"city_id": world["par"]["id"], "name": "Demo bistro", "is_demo": True}).json()
    iid = itinerary["id"]
    d = planner_client.post(f"{API}/itineraries/{iid}/edit").json()
    stay = next(s for s in d["stays"] if s["city_id"] == world["par"]["id"])
    planner_client.put(f"{API}/itineraries/{iid}/stays/{stay['id']}/hotel", json={"hotel_id": used["id"]})

    assert planner_client.get(f"{API}/admin/demo-data").status_code == 403
    summary = admin_client.get(f"{API}/admin/demo-data").json()
    assert summary["hotels"]["demo"] >= 2 and summary["hotels"]["in_use"] >= 1 and summary["restaurants"]["demo"] >= 1
    result = admin_client.post(f"{API}/admin/demo-data/remove").json()
    assert result["hotels"]["deleted"] >= 1 and result["hotels"]["deactivated"] >= 1

    assert admin_client.get(f"{API}/inventory/hotels/{unused['id']}").status_code == 404
    kept = admin_client.get(f"{API}/inventory/hotels/{used['id']}").json()
    assert kept["is_active"] is False
    assert admin_client.get(f"{API}/inventory/restaurants/{rest['id']}").status_code == 404
    after = planner_client.get(f"{API}/itineraries/{iid}").json()
    assert next(s for s in after["stays"] if s["city_id"] == world["par"]["id"])["hotel"]["id"] == used["id"]
    assert admin_client.get(f"{API}/admin/demo-data").json()["hotels"]["demo"] == 0  # nothing active left


# ------------------------------------------------------------------ templates
def test_save_and_use_template_moves_dates(planner_client, itinerary, world):
    iid = itinerary["id"]
    src = planner_client.get(f"{API}/itineraries/{iid}").json()
    r = planner_client.post(f"{API}/itineraries/{iid}/save-as-template", json={"title": "Benelux & Alps 10 days", "description": "Family favourite"})
    assert r.status_code == 201, r.text
    tpl = r.json()
    assert tpl["enquiry_id"] is None and tpl["is_locked"] and tpl["total_days"] == src["total_days"]
    assert any(t["id"] == tpl["id"] for t in planner_client.get(f"{API}/itinerary-templates").json())
    assert all(i["id"] != tpl["id"] for i in planner_client.get(f"{API}/itineraries", params={"page_size": 100}).json()["items"])

    agent = planner_client.post(f"{API}/travel-agents", json={"company_name": f"Tpl Agency {_uid()}"}).json()
    cust = planner_client.post(f"{API}/customers", json={"travel_agent_id": agent["id"], "name": "Tpl Family", "adults": 2}).json()
    enq = planner_client.post(f"{API}/enquiries", json={"travel_agent_id": agent["id"], "customer_id": cust["id"], "adults": 2}).json()
    planner_client.put(f"{API}/enquiries/{enq['id']}/requirements", json={"adults": 2, "arrival_date": "2027-09-01", "departure_date": "2027-09-10"})
    r = planner_client.post(f"{API}/enquiries/{enq['id']}/itineraries/from-template", json={"template_id": tpl["id"]})
    assert r.status_code == 201, r.text
    new = planner_client.get(f"{API}/itineraries/{r.json()['id']}").json()
    assert new["enquiry_id"] == enq["id"] and new["start_date"] == "2027-09-01" and new["total_days"] == src["total_days"]
    assert new["days"][0]["date"] == "2027-09-01" and new["days"][-1]["date"] == f"2027-09-{src['total_days']:02d}"
    assert [d["title"] for d in new["days"]] == [d["title"] for d in src["days"]]
    assert new["is_locked"] and "template" in (new["version_notes"] or "").lower()

    assert planner_client.delete(f"{API}/itinerary-templates/{tpl['id']}").status_code == 204
    assert all(t["id"] != tpl["id"] for t in planner_client.get(f"{API}/itinerary-templates").json())
    assert planner_client.post(f"{API}/enquiries/{enq['id']}/itineraries/from-template", json={"template_id": tpl["id"]}).status_code == 404
    assert planner_client.delete(f"{API}/itinerary-templates/{iid}").status_code == 404  # a proposal is not a template


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="Open-file locking check is Windows-specific")
def test_restore_refuses_while_the_database_is_open(install):
    settings, db_path = install
    svc = BackupService(settings=settings)
    b = svc.create()
    con = sqlite3.connect(db_path)  # simulates the running app
    try:
        with pytest.raises(DomainError, match="Stop YANA Travel Studio first"):
            svc.restore(settings.backups_dir / b["name"])
    finally:
        con.close()
    assert len(svc.list()) == 1  # refused before taking a safety backup
