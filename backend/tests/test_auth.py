from tests.conftest import ADMIN, PLANNER


def test_login_sets_httponly_cookie_and_me_returns_user(client):
    r = client.post("/api/v1/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})
    assert r.status_code == 200
    assert r.json()["role"]["code"] == "admin"
    cookie_header = r.headers["set-cookie"].lower()
    assert "httponly" in cookie_header and "samesite=lax" in cookie_header
    assert r.json().get("password_hash") is None

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == ADMIN["email"]


def test_login_is_case_insensitive_on_email(client):
    r = client.post("/api/v1/auth/login", json={"email": PLANNER["email"].upper(), "password": PLANNER["password"]})
    assert r.status_code == 200


def test_wrong_password_and_unknown_email_give_same_error(client):
    wrong = client.post("/api/v1/auth/login", json={"email": ADMIN["email"], "password": "nope-nope"})
    unknown = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_protected_endpoints_require_login(client):
    for path in ("/api/v1/auth/me", "/api/v1/travel-agents", "/api/v1/enquiries", "/api/v1/dashboard/summary"):
        r = client.get(path)
        assert r.status_code == 401, path
        assert r.json()["error"] == "not_authenticated"


def test_tampered_token_rejected(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


def test_logout_clears_session(admin_client):
    assert admin_client.post("/api/v1/auth/logout").status_code == 204
    assert admin_client.get("/api/v1/auth/me").status_code == 401


def test_health_stays_public(client):
    assert client.get("/api/v1/health").status_code == 200
