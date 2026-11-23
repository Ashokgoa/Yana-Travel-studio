import pytest

from app.services.login_throttle import LoginThrottle, login_throttle
from tests.conftest import PLANNER


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_locks_after_max_failures_and_unlocks_after_lockout():
    clock = FakeClock()
    t = LoginThrottle(max_failures=3, window_seconds=60, lockout_seconds=120, clock=clock)
    for _ in range(2):
        t.record_failure("A@x.com")
    assert t.retry_after("a@x.com") == 0
    t.record_failure("a@x.com")
    assert t.retry_after("a@x.com") == 120
    clock.now += 121
    assert t.retry_after("a@x.com") == 0


def test_failures_outside_window_do_not_count():
    clock = FakeClock()
    t = LoginThrottle(max_failures=3, window_seconds=60, lockout_seconds=120, clock=clock)
    t.record_failure("a@x.com")
    t.record_failure("a@x.com")
    clock.now += 61
    t.record_failure("a@x.com")
    assert t.retry_after("a@x.com") == 0


def test_success_clears_failures():
    t = LoginThrottle(max_failures=2, window_seconds=60, lockout_seconds=60, clock=FakeClock())
    t.record_failure("a@x.com")
    t.record_success("a@x.com")
    t.record_failure("a@x.com")
    assert t.retry_after("a@x.com") == 0


@pytest.fixture()
def fresh_throttle():
    login_throttle.reset()
    yield
    login_throttle.reset()


def test_api_returns_429_after_repeated_wrong_passwords(client, fresh_throttle):
    wrong = {"email": PLANNER["email"], "password": "wrong-password"}
    for _ in range(login_throttle.max_failures):
        assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    # Locked: even the correct password is refused until the lockout ends.
    r = client.post("/api/v1/auth/login", json={"email": PLANNER["email"], "password": PLANNER["password"]})
    assert r.status_code == 429
    assert r.json()["error"] == "too_many_attempts" and "Try again in 15 minutes" in r.json()["message"]


def test_lockout_is_per_account(client, fresh_throttle):
    for _ in range(login_throttle.max_failures):
        client.post("/api/v1/auth/login", json={"email": "victim@example.com", "password": "nope-nope"})
    r = client.post("/api/v1/auth/login", json={"email": PLANNER["email"], "password": PLANNER["password"]})
    assert r.status_code == 200
