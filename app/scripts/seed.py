"""
Create the bootstrap accounts.

    python -m app.scripts.seed

Idempotent: an account that already exists is left exactly as it is, so this is
safe to re-run after a migration or a fresh deploy. Credentials come from the
environment, never from this file — see SEED_* in `.env.example`.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, dispose_engine
from app.models.user import Role, User
from app.repositories import user as user_repo

SEED_USERS = [
    (
        settings.SEED_SUPERADMIN_EMAIL,
        settings.SEED_SUPERADMIN_NAME,
        settings.SEED_SUPERADMIN_PASSWORD,
        Role.SUPERADMIN,
    ),
    (
        settings.SEED_ADMIN_EMAIL,
        settings.SEED_ADMIN_NAME,
        settings.SEED_ADMIN_PASSWORD,
        Role.ADMIN,
    ),
]


async def seed() -> int:
    configured = [row for row in SEED_USERS if row[0] and row[2]]

    if not configured:
        print("Nothing to seed: set SEED_* values in .env first.", file=sys.stderr)
        return 1

    async with SessionLocal() as db:
        for email, name, password, role in configured:
            email = email.strip().lower()

            if await user_repo.get_by_email(db, email):
                print(f"  = {email} already exists, left untouched")
                continue

            db.add(
                User(
                    email=email,
                    full_name=name,
                    password_hash=hash_password(password),
                    role=role.value,
                )
            )
            print(f"  + {email} created as {role.value}")

        await db.commit()

    return 0


async def main() -> int:
    try:
        return await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
