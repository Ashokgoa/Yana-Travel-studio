"""Password hashing (Argon2 via pwdlib) and signed access tokens (JWT, HS256)."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

_password_hash = PasswordHash.recommended()

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        # Still spend time hashing so response timing doesn't reveal unknown accounts.
        _password_hash.hash(password)
        return False
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> int | None:
    """Return the user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
