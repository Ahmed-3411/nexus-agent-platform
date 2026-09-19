"""
Thin data-access layer for users and roles.

Kept separate from api/auth.py so that:
  - route handlers stay focused on request/response shape and HTTP
    status codes, not query construction;
  - tests can mock these functions directly (test_auth_api.py) instead
    of mocking a full async SQLAlchemy session's query internals.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Role, User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.email == email))
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    hashed_password: str,
    role_name: str,
    full_name: str | None = None,
) -> User:
    """
    Create a user with the given role.

    Raises ValueError if `role_name` doesn't exist (it should always
    exist for the built-in roles seeded in schema.sql, but this guards
    against a typo or an out-of-sync database).
    """
    role = await get_role_by_name(db, role_name)
    if role is None:
        raise ValueError(f"Role '{role_name}' does not exist.")

    user = User(email=email, hashed_password=hashed_password, full_name=full_name, role_id=role.id)
    db.add(user)
    await db.commit()

    # Re-fetch with the role relationship eagerly loaded rather than
    # relying on db.refresh() to populate it correctly post-commit.
    return await get_user_by_email(db, email)
