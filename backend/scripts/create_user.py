"""
Bootstrap a user directly against the database, with any built-in role.

There is no API endpoint for this (see api/auth.py's docstring:
self-registration only ever grants the "analyst" role, on purpose). This
script exists specifically to create the *first* admin/manager/etc.
account, since nothing else can.

Usage (from backend/, with the venv activated and DATABASE_URL configured):
    python -m scripts.create_user --email admin@example.com --password "..." --role admin
"""
import argparse
import asyncio

from auth.repository import create_user, get_user_by_email
from auth.security import hash_password
from db.session import AsyncSessionLocal


async def _main(email: str, password: str, role: str, full_name: str | None) -> None:
    async with AsyncSessionLocal() as db:
        existing = await get_user_by_email(db, email)
        if existing is not None:
            print(f"A user with email '{email}' already exists (id={existing.id}). Nothing to do.")
            return

        user = await create_user(
            db,
            email=email,
            hashed_password=hash_password(password),
            role_name=role,
            full_name=full_name,
        )
        print(f"Created user '{user.email}' with role '{user.role.name}' (id={user.id}).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--role", required=True, choices=["admin", "manager", "analyst", "support_agent"]
    )
    parser.add_argument("--full-name", default=None)
    args = parser.parse_args()

    asyncio.run(_main(args.email, args.password, args.role, args.full_name))


if __name__ == "__main__":
    main()
