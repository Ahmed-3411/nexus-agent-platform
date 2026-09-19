"""
Auth endpoints: self-service registration and login.

This is what closes the security gap left open in Phase 5: `role` used
to be a plain field on POST /workflows that any caller could set to
"admin". Now, role comes from a signed JWT issued here, based on what's
actually stored in the database for that user — a caller can no longer
just claim a role.

Self-registration always creates the user with role="analyst" (the
least-privileged built-in role), regardless of anything the client
sends — there is deliberately no "role" field on RegisterRequest at all,
so there's nothing to spoof. Promoting a user to a higher role (manager,
support_agent, admin) is an administrative action this phase doesn't
build an endpoint for yet; use backend/scripts/create_user.py to
bootstrap the first admin account directly against the database instead.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth.repository import create_user, get_user_by_email
from auth.security import create_access_token, hash_password, verify_password
from db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# The only role self-registration is allowed to grant. Not configurable
# via the request body on purpose — see this module's docstring.
SELF_SERVICE_ROLE = "analyst"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    user = await create_user(
        db,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role_name=SELF_SERVICE_ROLE,
        full_name=payload.full_name,
    )
    token = create_access_token(str(user.id), extra_claims={"role": user.role.name, "email": user.email})
    return TokenResponse(access_token=token, role=user.role.name)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await get_user_by_email(db, payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        # Deliberately identical error for "no such user" and "wrong
        # password" — distinguishing them lets an attacker enumerate
        # which emails are registered.
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    role_name = user.role.name if user.role else SELF_SERVICE_ROLE
    token = create_access_token(str(user.id), extra_claims={"role": role_name, "email": user.email})
    return TokenResponse(access_token=token, role=role_name)
