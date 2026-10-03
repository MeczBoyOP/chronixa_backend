"""
Password hashing and access tokens.

Two primitives and nothing else: bcrypt for storage, a signed JWT for the
session cookie. No auth framework — everything a login needs is below.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"

# bcrypt hashes at most 72 BYTES and SILENTLY IGNORES the rest, so two long
# passwords sharing a 72-byte prefix would authenticate each other. The schemas
# cap input at 72 instead of truncating here, so the ceiling surfaces as a
# validation error the user can read rather than as a silent collision.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """False for a wrong password AND for a malformed hash — never raises."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False


# Verified against when the email doesn't exist, so a missing user costs the
# same ~200ms as a wrong password. Without it, login answers "no such account"
# in microseconds and "wrong password" slowly, which is enough to enumerate who
# has an account. Generated per process; the value is never checked against.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            # `sub` is a string by spec — a numeric one makes some libraries
            # reject the token outright.
            "sub": str(user_id),
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Claims, or None for anything expired, forged or malformed."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
