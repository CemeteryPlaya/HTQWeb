"""
Data migration script: Django auth.User + mainView.Profile → User Service.

This script runs against the Django database and the User Service database.
It performs a one-time export/import of all user data.

Usage:
    # Run from project root (d:\HTQWeb1)
    python services/user/migrate_from_django.py

Prerequisites:
    1. User Service database schema created (alembic upgrade head)
    2. Both databases accessible
    3. Django settings module configured
"""

import asyncio
import os
import sys

import asyncpg
from django.contrib.auth.hashers import check_password

# ─── Configuration ──────────────────────────────────────────────────────────
DJANGO_DB_DSN = os.getenv(
    "DJANGO_DB_DSN",
    "postgresql://htqweb:change-me@localhost:55432/htqweb",
)
USER_SERVICE_DB_DSN = os.getenv(
    "USER_SERVICE_DB_DSN",
    "postgresql+asyncpg://htqweb:change-me@localhost:55432/htqweb",
)
# Schema for user service tables
USER_SCHEMA = os.getenv("USER_SCHEMA", "auth")


def verify_django_password(plain_password: str, hashed: str) -> bool:
    """Verify a Django password hash."""
    return check_password(plain_password, hashed)


async def get_django_users() -> list[dict]:
    """Fetch all users + profiles from Django database."""
    conn = await asyncpg.connect(DJANGO_DB_DSN)

    try:
        # Get base users
        rows = await conn.fetch("""
            SELECT
                u.id,
                u.username,
                u.email,
                u.password,
                u.first_name,
                u.last_name,
                u.is_active,
                u.is_staff,
                u.is_superuser,
                u.date_joined,
                u.last_login
            FROM auth_user u
            ORDER BY u.id
        """)

        users = []
        for row in rows:
            # Get profile data
            profile = await conn.fetchrow("""
                SELECT
                    display_name,
                    bio,
                    avatar,
                    patronymic,
                    phone,
                    settings,
                    must_change_password,
                    created_at,
                    updated_at
                FROM mainview_profile
                WHERE user_id = $1
            """, row["id"])

            # Determine status
            if not row["is_active"]:
                # Check if this is a pending registration or rejected
                # For simplicity, treat all inactive as pending
                status = "pending"
            else:
                status = "active"

            users.append({
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "password_hash": row["password"],  # Django's hashed password
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "patronymic": profile["patronymic"] if profile else "",
                "display_name": profile["display_name"] if profile else "",
                "bio": profile["bio"] if profile else "",
                "phone": profile["phone"] if profile else "",
                "avatar_url": f"/media/{profile['avatar']}" if profile and profile["avatar"] else None,
                "settings": profile["settings"] if profile and profile["settings"] else {},
                "status": status,
                "is_staff": row["is_staff"],
                "is_superuser": row["is_superuser"],
                "must_change_password": profile["must_change_password"] if profile else False,
                "date_joined": row["date_joined"],
                "last_login": row["last_login"],
                "created_at": profile["created_at"] if profile else row["date_joined"],
                "updated_at": profile["updated_at"] if profile else row["date_joined"],
            })

        return users

    finally:
        await conn.close()


async def insert_users(users: list[dict]) -> None:
    """Insert users into User Service database."""
    conn = await asyncpg.connect(USER_SERVICE_DB_DSN)

    try:
        # Set search_path to user schema
        await conn.execute(f"SET search_path TO {USER_SCHEMA}")

        # Check existing users to avoid duplicates
        existing_ids = await conn.fetch("SELECT id FROM users")
        existing_id_set = {r["id"] for r in existing_ids}

        inserted = 0
        skipped = 0

        for user in users:
            if user["id"] in existing_id_set:
                skipped += 1
                print(f"  Skipping user id={user['id']} ({user['username']}) — already exists")
                continue

            # Re-hash password with bcrypt (transparent upgrade from Django PBKDF2).
            # We can't re-hash without the plain password, so we keep the Django hash
            # and let verify_django_password verify it. The hash will be upgraded on next login.
            password_hash = user["password_hash"]

            await conn.execute(
                """
                INSERT INTO users (
                    id, username, email, password_hash,
                    first_name, last_name, patronymic, display_name,
                    bio, phone, avatar_url, settings,
                    status, is_staff, is_superuser, must_change_password,
                    date_joined, last_login, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                """,
                user["id"],
                user["username"],
                user["email"].lower(),
                password_hash,
                user["first_name"],
                user["last_name"],
                user["patronymic"],
                user["display_name"],
                user["bio"],
                user["phone"],
                user["avatar_url"],
                user["settings"],
                user["status"],
                user["is_staff"],
                user["is_superuser"],
                user["must_change_password"],
                user["date_joined"],
                user["last_login"],
                user["created_at"],
                user["updated_at"],
            )
            inserted += 1
            print(f"  + User id={user['id']} ({user['username']})")

        # Update sequence
        if users:
            max_id = max(u["id"] for u in users)
            await conn.execute(f"SELECT setval('users_id_seq', {max_id})")

        print(f"\nMigration complete: {inserted} inserted, {skipped} skipped")

    finally:
        await conn.close()


async def verify_migration() -> None:
    """Verify that all Django users exist in User Service."""
    django_conn = await asyncpg.connect(DJANGO_DB_DSN)
    user_conn = await asyncpg.connect(USER_SERVICE_DB_DSN)

    try:
        await user_conn.execute(f"SET search_path TO {USER_SCHEMA}")

        django_count = await django_conn.fetchval("SELECT count(*) FROM auth_user")
        user_count = await user_conn.fetchval("SELECT count(*) FROM users")

        print(f"\nVerification:")
        print(f"  Django auth.users:  {django_count}")
        print(f"  User Service users: {user_count}")

        if django_count == user_count:
            print("  ✓ Counts match")
        else:
            print(f"  ✗ MISMATCH: {django_count - user_count} users missing")

        # Check specific users
        django_users = await django_conn.fetch("SELECT id, username, email FROM auth_user ORDER BY id")
        user_users = await user_conn.fetch("SELECT id, username, email FROM users ORDER BY id")

        django_set = {(u["username"], u["email"]) for u in django_users}
        user_set = {(u["username"], u["email"]) for u in user_users}

        missing = django_set - user_set
        if missing:
            print(f"  ✗ Missing users: {missing}")
        else:
            print("  ✓ All users present")

    finally:
        await django_conn.close()
        await user_conn.close()


async def main():
    print("=" * 60)
    print("Django → User Service Data Migration")
    print("=" * 60)

    print("\n1. Fetching users from Django...")
    users = await get_django_users()
    print(f"   Found {len(users)} users")

    print("\n2. Inserting into User Service...")
    await insert_users(users)

    print("\n3. Verifying...")
    await verify_migration()


if __name__ == "__main__":
    asyncio.run(main())
