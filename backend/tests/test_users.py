import uuid


def _email():
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


def test_planner_cannot_manage_users(planner_client):
    assert planner_client.get("/api/v1/users").status_code == 403
    r = planner_client.post("/api/v1/users", json={"email": _email(), "full_name": "X", "role": "admin", "password": "password123"})
    assert r.status_code == 403


def test_admin_creates_planner_who_can_log_in(admin_client, client):
    email = _email()
    r = admin_client.post("/api/v1/users", json={"email": email, "full_name": "New Planner", "role": "planner", "password": "password123"})
    assert r.status_code == 201 and r.json()["role"]["code"] == "planner"
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "password123"}).status_code == 200


def test_duplicate_email_rejected(admin_client):
    email = _email()
    body = {"email": email, "full_name": "A", "role": "planner", "password": "password123"}
    assert admin_client.post("/api/v1/users", json=body).status_code == 201
    r = admin_client.post("/api/v1/users", json={**body, "email": email.upper()})
    assert r.status_code == 409


def test_short_password_rejected_with_field_detail(admin_client):
    r = admin_client.post("/api/v1/users", json={"email": _email(), "full_name": "A", "role": "planner", "password": "short"})
    assert r.status_code == 422
    assert r.json()["details"][0]["field"] == "password"


def test_deactivated_user_cannot_log_in(admin_client, client):
    email = _email()
    uid = admin_client.post("/api/v1/users", json={"email": email, "full_name": "A", "role": "planner", "password": "password123"}).json()["id"]
    assert admin_client.patch(f"/api/v1/users/{uid}", json={"is_active": False}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "password123"}).status_code == 401


def test_admin_cannot_deactivate_self(admin_client):
    me = admin_client.get("/api/v1/auth/me").json()
    r = admin_client.patch(f"/api/v1/users/{me['id']}", json={"is_active": False})
    assert r.status_code == 409
