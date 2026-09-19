"""
Password hashing and JWT token creation/verification.

This module is pure logic — no FastAPI dependencies, no database access —
so it's fully unit-testable on its own. `auth/dependencies.py` (not yet
built; needed once login endpoints exist) will wrap `decode_access_token`
in a FastAPI dependency that pulls the token from the request and loads
the corresponding user.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


class TokenError(ValueError):
    """Raised when a JWT is missing, malformed, expired, or has a bad signature."""


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT for the given subject (typically the user id).

    `extra_claims` can carry things like role or email so downstream code
    doesn't need a DB round-trip just to check the role on every request.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising TokenError on any problem."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
