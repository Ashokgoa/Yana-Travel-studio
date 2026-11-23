"""Brute-force protection for sign-in.

After `max_failures` wrong passwords for the same email within `window`, that
email is locked for `lockout`. A successful sign-in clears the counter.

Keyed by email (not IP): behind the Next.js proxy every request comes from
127.0.0.1, and per-account limits are what stop password guessing. State is
in memory, which is correct for the single local server process; a multi-instance
cloud deployment should move this to the database or a cache.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Entry:
    failures: list[float] = field(default_factory=list)
    locked_until: float = 0.0


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_seconds: int = 15 * 60, lockout_seconds: int = 15 * 60, clock=time.monotonic):
        self.max_failures = max_failures
        self.window = window_seconds
        self.lockout = lockout_seconds
        self._clock = clock
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(email: str) -> str:
        return email.strip().lower()

    def retry_after(self, email: str) -> int:
        """Seconds until this email may try again (0 = allowed now)."""
        with self._lock:
            entry = self._entries.get(self._key(email))
            if not entry:
                return 0
            remaining = entry.locked_until - self._clock()
            return max(0, int(remaining + 0.999))

    def record_failure(self, email: str) -> None:
        now = self._clock()
        with self._lock:
            entry = self._entries.setdefault(self._key(email), _Entry())
            entry.failures = [t for t in entry.failures if now - t < self.window] + [now]
            if len(entry.failures) >= self.max_failures:
                entry.locked_until = now + self.lockout
                entry.failures.clear()
            self._prune(now)

    def record_success(self, email: str) -> None:
        with self._lock:
            self._entries.pop(self._key(email), None)

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune(self, now: float) -> None:
        # Keep memory bounded: drop entries with no recent failures and no active lock.
        if len(self._entries) < 1000:
            return
        stale = [k for k, e in self._entries.items() if e.locked_until <= now and not any(now - t < self.window for t in e.failures)]
        for k in stale:
            del self._entries[k]


login_throttle = LoginThrottle()
