"""
The auth primitives, without a database.

Everything here is pure: hashing, signing, and the validation boundary. The
endpoints need Postgres and are covered separately.
"""

import pytest
from pydantic import ValidationError

from app.core import security
from app.core.security import (
    MAX_PASSWORD_BYTES,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import LoginRequest


def test_hash_is_not_the_password() -> None:
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)


def test_wrong_password_fails() -> None:
    assert not verify_password("wrong", hash_password("right"))


def test_salt_makes_every_hash_unique() -> None:
    """Two identical passwords must not produce the same stored value."""
    assert hash_password("same") != hash_password("same")


def test_malformed_hash_returns_false_rather_than_raising() -> None:
    """A corrupt row must fail the login, not 500 the endpoint."""
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_token_round_trip() -> None:
    claims = decode_access_token(create_access_token(7, "superadmin"))
    assert claims is not None
    assert claims["sub"] == "7"  # string by JWT spec, not int
    assert claims["role"] == "superadmin"


def test_tampered_token_is_rejected() -> None:
    token = create_access_token(1, "admin")
    assert decode_access_token(token[:-1] + ("A" if token[-1] != "A" else "B")) is None


def test_token_signed_with_another_key_is_rejected() -> None:
    import jwt

    forged = jwt.encode({"sub": "1", "role": "superadmin"}, "not-our-key", "HS256")
    assert decode_access_token(forged) is None


def test_expired_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
    assert decode_access_token(create_access_token(1, "admin")) is None


def test_login_schema_rejects_passwords_past_bcrypts_ceiling() -> None:
    """
    The guard that stops bcrypt silently truncating. Without it, two passwords
    sharing a 72-byte prefix would authenticate each other.
    """
    with pytest.raises(ValidationError):
        LoginRequest(email="a@b.com", password="x" * (MAX_PASSWORD_BYTES + 1))


def test_login_schema_rejects_a_non_email() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="123456")
