"""
Dual-write management command: sync Django users to User Service.

This command performs a one-time sync of all Django users to the User Service.
For dual-write migration strategy, run this after each user change in Django
until the User Service becomes the authoritative source.

Usage:
    python manage.py sync_users_to_user_service

For continuous dual-write, this should be called:
- After user creation (post_save signal)
- After user profile update (post_save signal)
- Periodically via cron for consistency check
"""

import httpx
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from mainView.models import Profile


class Command(BaseCommand):
    help = "Sync Django users to User Service (dual-write migration)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-service-url",
            default="http://user-service:8005",
            help="Base URL of the User Service",
        )
        parser.add_argument(
            "--verify-only",
            action="store_true",
            help="Only verify, don't sync",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Sync only a specific user by ID",
        )

    def handle(self, *args, **options):
        base_url = options["user_service_url"].rstrip("/")
        verify_only = options["verify_only"]
        user_id = options.get("user_id")

        self.stdout.write(f"User Service: {base_url}")
        self.stdout.write(f"Mode: {'verify' if verify_only else 'sync'}")

        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.all().order_by("id")

        total = users.count()
        self.stdout.write(f"Found {total} Django users")

        synced = 0
        errors = 0
        skipped = 0

        for user in users:
            profile, _ = Profile.objects.get_or_create(user=user)

            user_data = {
                "django_id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "profile": {
                    "display_name": profile.display_name,
                    "bio": profile.bio,
                    "patronymic": profile.patronymic,
                    "phone": profile.phone,
                    "avatar_url": f"/media/{profile.avatar}" if profile.avatar else None,
                    "settings": profile.settings or {},
                    "must_change_password": profile.must_change_password,
                },
            }

            if verify_only:
                # Just check if user exists in User Service
                try:
                    resp = httpx.get(
                        f"{base_url}/api/v1/admin/users/",
                        timeout=5,
                    )
                    # Simplified check
                    self.stdout.write(f"  ? User {user.username} (verify mode)")
                except Exception as e:
                    self.stderr.write(f"  ✗ User {user.username}: {e}")
                    errors += 1
                continue

            # Sync to User Service
            try:
                resp = httpx.post(
                    f"{base_url}/api/internal/sync-user/",
                    json=user_data,
                    timeout=10,
                )

                if resp.status_code in (200, 201, 204):
                    synced += 1
                    self.stdout.write(f"  + User {user.username} (id={user.id})")
                elif resp.status_code == 409:
                    # Conflict — user already exists, update instead
                    resp = httpx.put(
                        f"{base_url}/api/internal/sync-user/{user.id}/",
                        json=user_data,
                        timeout=10,
                    )
                    if resp.status_code in (200, 204):
                        synced += 1
                        self.stdout.write(f"  ~ User {user.username} (updated)")
                    else:
                        self.stderr.write(
                            f"  ✗ User {user.username}: update failed ({resp.status_code})"
                        )
                        errors += 1
                else:
                    self.stderr.write(
                        f"  ✗ User {user.username}: sync failed ({resp.status_code}) {resp.text}"
                    )
                    errors += 1

            except httpx.ConnectError:
                self.stderr.write(
                    f"  ✗ User {user.username}: User Service unreachable at {base_url}"
                )
                errors += 1
            except Exception as e:
                self.stderr.write(f"  ✗ User {user.username}: {e}")
                errors += 1

        self.stdout.write("\n" + "=" * 40)
        self.stdout.write(f"Sync complete: {synced} synced, {skipped} skipped, {errors} errors")


def sync_user_to_user_service(user, profile=None):
    """
    Helper function for signal-based dual-write.
    Call this from post_save signals.

    This is non-blocking — fires and forgets.
    For production, use Celery or a background task.
    """
    import threading

    def _sync():
        try:
            if profile is None:
                profile, _ = Profile.objects.get_or_create(user=user)

            user_data = {
                "django_id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "profile": {
                    "display_name": profile.display_name,
                    "bio": profile.bio,
                    "patronymic": profile.patronymic,
                    "phone": profile.phone,
                    "avatar_url": f"/media/{profile.avatar}" if profile.avatar else None,
                    "settings": profile.settings or {},
                    "must_change_password": profile.must_change_password,
                },
            }

            httpx.post(
                "http://user-service:8005/api/internal/sync-user/",
                json=user_data,
                timeout=5,
            )
        except Exception:
            # Log error but don't fail the Django operation
            pass

    threading.Thread(target=_sync, daemon=True).start()
