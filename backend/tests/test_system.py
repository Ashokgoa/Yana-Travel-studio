def test_health_reports_ok_after_migration(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["database"]["status"] == "ok"
    assert f"migration {_head_revision()}" in body["database"]["detail"]


def _head_revision() -> str:
    from alembic.script import ScriptDirectory

    from tests.conftest import alembic_config

    return ScriptDirectory.from_config(alembic_config("sqlite://")).get_current_head()


def test_startup_creates_storage_layout(client, tmp_root):
    for folder in ("logo", "countries", "hotels", "restaurants", "sightseeing", "generated"):
        assert (tmp_root / "uploads" / folder).is_dir()
    assert (tmp_root / "exports" / "itineraries").is_dir()


def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/health" in schema["paths"]


def test_unknown_route_returns_json_error(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "http_error"


def test_cors_allows_frontend_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
