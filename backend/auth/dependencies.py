"""
FastAPI dependency that extracts and validates the bearer JWT from the
Authorization header, returning the authenticated user's id/email/role.

The role is read directly from the token's claims (embedded at login
time — see api/auth.py) rather than looked up from the database again on
every request. Tradeoff: if a user's role changes in the database, that
change won't take effect for them until they log in again or their
current token expires (see JWT_EXPIRE_MINUTES in core/config.py). This
is an acceptable tradeoff for now — forcing a DB round-trip on every
request would give up most of the point of using JWTs — but revisit this
if role changes need to take effect immediately (e.g. a token blocklist
or much shorter token lifetime).
"""
from dataclasses import dataclass

from fastapi import Header, HTTPException

from auth.security import TokenError, decode_access_token


@dataclass
class CurrentUser:
    id: str
    email: str | None
    role: str


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc

    subject = payload.get("sub")
    role = payload.get("role")
    if not subject or not role:
        raise HTTPException(status_code=401, detail="Token is missing required claims.")

    return CurrentUser(id=subject, email=payload.get("email"), role=role)
