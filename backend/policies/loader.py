"""
DB-backed role -> permissions loader for the Policy Engine.

This is the production counterpart to policies/default_roles.py's
hardcoded DEFAULT_ROLE_PERMISSIONS: it reads the real `roles` and
`permissions` tables (joined through `role_permissions`) so that
permission changes made through the (future) admin UI take effect
without a code deploy.

Not yet wired into the FastAPI app in this phase — see PolicyEngine's
docstring for why: the API layer doesn't carry an authenticated user's
role into a workflow run yet. When it does, a route dependency should
call `load_role_permissions(db)` once per request (or cache it with a
short TTL) and pass the result into `PolicyEngine(role_permissions=...)`.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Role


async def load_role_permissions(db: AsyncSession) -> dict[str, set[str]]:
    """Build a {role_name: {permission_code, ...}} map from the database."""
    result = await db.execute(select(Role).options(selectinload(Role.permissions)))
    roles = result.scalars().all()
    return {role.name: {p.code for p in role.permissions} for role in roles}
