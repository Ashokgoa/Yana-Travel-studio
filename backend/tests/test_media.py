import io
import random

import pytest
from PIL import Image

from app.utils.images import MAX_EDGE, ImageError, process_image
from tests.conftest import unique_iso

API = "/api/v1"


def make_image(fmt="JPEG", size=(800, 600), color=None, exif_gps=False) -> bytes:
    color = color or tuple(random.randint(0, 255) for _ in range(3))
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    kwargs = {}
    if exif_gps:
        exif = Image.Exif()
        exif[0x8825] = {1: "N", 2: (52.0, 22.0, 3.0)}  # GPSInfo
        exif[0x010F] = "PhoneMaker"  # camera make
        kwargs["exif"] = exif
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def upload(c, data, name="photo.jpg", **form):
    return c.post(f"{API}/media/upload", files={"file": (name, data, "application/octet-stream")}, data=form)


@pytest.fixture()
def hotel(admin_client):
    country = admin_client.post(f"{API}/inventory/countries", json={"name": f"Imgland {random.randint(0, 10**9)}", "iso_code": unique_iso()})
    assert country.status_code == 201, country.text
    city = admin_client.post(f"{API}/inventory/cities", json={"country_id": country.json()["id"], "name": "Pic City"}).json()
    return admin_client.post(f"{API}/inventory/hotels", json={"city_id": city["id"], "name": "Photo Hotel"}).json()


# ------------------------------------------------------------------ processing (unit)
def test_processing_strips_metadata_and_downscales():
    raw = make_image(size=(4000, 3000), exif_gps=True)
    assert Image.open(io.BytesIO(raw)).getexif()  # input has EXIF/GPS
    out = process_image(raw, 10 * 1_048_576)
    assert max(out.width, out.height) == MAX_EDGE
    stored = Image.open(io.BytesIO(out.data))
    assert not stored.getexif(), "all metadata, including GPS, must be removed"
    assert max(Image.open(io.BytesIO(out.thumbnail)).size) <= 480


@pytest.mark.parametrize("payload, message", [
    (b"", "empty"),
    (b"this is not an image at all", "not a valid image"),
    (b"GIF89a" + b"\x00" * 50, "not a valid image"),
])
def test_processing_rejects_bad_files(payload, message):
    with pytest.raises(ImageError, match=message):
        process_image(payload, 10 * 1_048_576)


def test_processing_rejects_unsupported_format():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "GIF")
    with pytest.raises(ImageError, match="Unsupported"):
        process_image(buf.getvalue(), 10 * 1_048_576)


def test_processing_rejects_oversized_file():
    with pytest.raises(ImageError, match="too large"):
        process_image(b"x" * 2_000_000, 1_048_576)


# ------------------------------------------------------------------ API: upload & library
def test_library_upload_by_planner_and_dedupe(planner_client):
    data = make_image()
    r = upload(planner_client, data, description="Sunset over canals")
    assert r.status_code == 201, r.text
    first = r.json()
    assert first["created"] is True and first["media"]["category"] == "library"
    again = upload(planner_client, data, name="copy.jpg").json()
    assert again["created"] is False and again["media"]["id"] == first["media"]["id"]

    file = planner_client.get(first["media"]["url"])
    assert file.status_code == 200 and file.headers["content-type"] == "image/jpeg"
    assert "immutable" in file.headers["cache-control"]
    thumb = planner_client.get(first["media"]["thumbnail_url"])
    assert thumb.status_code == 200 and len(thumb.content) < len(file.content)

    found = planner_client.get(f"{API}/media", params={"q": "sunset"}).json()
    assert first["media"]["id"] in [m["id"] for m in found["items"]]


def test_upload_rejects_fake_image_with_clear_message(planner_client):
    r = upload(planner_client, b"<html>not a picture</html>", name="hotel.jpg")
    assert r.status_code == 422 and r.json()["error"] == "invalid_image"
    assert "not a valid image" in r.json()["message"]


def test_files_require_login(client, planner_client):
    media = upload(planner_client, make_image()).json()["media"]
    assert client.get(media["url"]).status_code == 401


def test_ai_images_are_always_illustrative(admin_client):
    m = upload(admin_client, make_image(), is_ai_generated="true", source="ai_generated").json()["media"]
    assert m["is_ai_generated"] and m["is_illustrative"]
    r = admin_client.patch(f"{API}/media/{m['id']}", json={"is_illustrative": False})
    assert r.json()["is_illustrative"] is True


# ------------------------------------------------------------------ API: galleries
def test_gallery_primary_reorder_caption_unlink(admin_client, hotel):
    up1 = upload(admin_client, make_image(), entity_type="hotel", entity_id=str(hotel["id"])).json()
    up2 = upload(admin_client, make_image(), entity_type="hotel", entity_id=str(hotel["id"])).json()
    assert up1["media"]["category"] == "hotel" and up1["link_id"]
    gallery = admin_client.get(f"{API}/media/gallery/hotel/{hotel['id']}").json()
    assert [g["is_primary"] for g in gallery] == [True, False]  # first upload becomes primary

    # list views show the primary thumbnail
    listed = admin_client.get(f"{API}/inventory/hotels/{hotel['id']}").json()
    assert listed["primary_image_url"] == up1["media"]["thumbnail_url"]

    gallery = admin_client.post(f"{API}/media/links/{gallery[1]['id']}/primary").json()
    assert [g["media_id"] for g in gallery if g["is_primary"]] == [up2["media"]["id"]]

    ids = [g["id"] for g in gallery]
    gallery = admin_client.put(f"{API}/media/gallery/hotel/{hotel['id']}/order", json={"link_ids": ids[::-1]}).json()
    assert [g["id"] for g in gallery] == ids[::-1]
    assert admin_client.put(f"{API}/media/gallery/hotel/{hotel['id']}/order", json={"link_ids": ids[:1]}).status_code == 400

    gallery = admin_client.put(f"{API}/media/links/{gallery[0]['id']}/caption", json={"caption": "Lobby"}).json()
    assert gallery[0]["caption"] == "Lobby"

    # removing the primary promotes the next image; the file stays in the library
    primary = next(g for g in gallery if g["is_primary"])
    gallery = admin_client.delete(f"{API}/media/links/{primary['id']}").json()
    assert len(gallery) == 1 and gallery[0]["is_primary"] is True
    assert admin_client.get(f"{API}/media/{primary['media_id']}").status_code == 200


def test_reuse_library_image_in_two_records(admin_client, hotel):
    media = upload(admin_client, make_image()).json()["media"]
    city_id = hotel["city"]["id"]
    admin_client.post(f"{API}/media/links", json={"entity_type": "hotel", "entity_id": hotel["id"], "media_id": media["id"]})
    admin_client.post(f"{API}/media/links", json={"entity_type": "city", "entity_id": city_id, "media_id": media["id"]})
    dup = admin_client.post(f"{API}/media/links", json={"entity_type": "city", "entity_id": city_id, "media_id": media["id"]})
    assert dup.status_code == 409
    detail = admin_client.get(f"{API}/media/{media['id']}").json()
    assert detail["usage_count"] == 2 and {u["entity_type"] for u in detail["usages"]} == {"hotel", "city"}
    assert any(u["entity_name"] == "Photo Hotel" for u in detail["usages"])


def test_replace_keeps_links_and_changes_url(admin_client, hotel):
    up = upload(admin_client, make_image(), entity_type="hotel", entity_id=str(hotel["id"])).json()
    old_url = up["media"]["url"]
    r = admin_client.post(f"{API}/media/{up['media']['id']}/replace", files={"file": ("new.png", make_image("PNG"), "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["url"] != old_url and r.json()["mime_type"] == "image/png"
    gallery = admin_client.get(f"{API}/media/gallery/hotel/{hotel['id']}").json()
    assert gallery[0]["media_id"] == up["media"]["id"]
    assert admin_client.get(r.json()["url"]).headers["content-type"] == "image/png"


def test_delete_removes_files_and_links(admin_client, hotel, tmp_root):
    up = upload(admin_client, make_image(), entity_type="hotel", entity_id=str(hotel["id"])).json()
    before = {p for p in (tmp_root / "uploads" / "hotels").rglob("*") if p.is_file()}
    assert admin_client.delete(f"{API}/media/{up['media']['id']}").status_code == 204
    after = {p for p in (tmp_root / "uploads" / "hotels").rglob("*") if p.is_file()}
    assert len(before - after) == 2  # image + thumbnail
    assert admin_client.get(f"{API}/media/gallery/hotel/{hotel['id']}").json() == []


def test_planner_cannot_change_inventory_galleries(planner_client, admin_client, hotel):
    r = upload(planner_client, make_image(), entity_type="hotel", entity_id=str(hotel["id"]))
    assert r.status_code == 403
    media = upload(planner_client, make_image()).json()["media"]
    assert planner_client.post(f"{API}/media/links", json={"entity_type": "hotel", "entity_id": hotel["id"], "media_id": media["id"]}).status_code == 403
    assert planner_client.delete(f"{API}/media/{media['id']}").status_code == 403
    assert planner_client.get(f"{API}/media/gallery/hotel/{hotel['id']}").status_code == 200


def test_gallery_for_unknown_record(admin_client):
    assert admin_client.get(f"{API}/media/gallery/hotel/999999").status_code == 404
