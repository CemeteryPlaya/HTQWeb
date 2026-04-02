"""
Management command to sync all existing users into ChatUserReplica.

Run once after initial messenger setup:
    python manage.py sync_chat_users

Also useful after bulk user imports or manual database edits.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from messenger.infrastructure.event_bus import _sync_user_replica


class Command(BaseCommand):
    help = 'Sync all existing users into ChatUserReplica for the messenger module'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()
        total = users.count()
        synced = 0

        self.stdout.write(f'Syncing {total} users into ChatUserReplica...')

        for user in users:
            try:
                _sync_user_replica(user)
                synced += 1
            except Exception as e:
                self.stderr.write(f'  ✗ Failed to sync user {user.pk} ({user.username}): {e}')

        self.stdout.write(self.style.SUCCESS(f'Done! Synced {synced}/{total} users.'))
