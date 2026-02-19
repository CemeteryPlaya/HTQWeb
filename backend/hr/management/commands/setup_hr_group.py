"""
Management command to set up HR RBAC groups:
    • senior_hr — полные права (all HR permissions)
    • junior_hr — только просмотр (view-only)

Usage:
    python manage.py setup_hr_group
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from hr.roles import SENIOR_HR_GROUP, JUNIOR_HR_GROUP, LEGACY_SENIOR_GROUPS, LEGACY_JUNIOR_GROUPS


class Command(BaseCommand):
    help = 'Create / sync senior_hr & junior_hr groups with correct permissions.'

    def handle(self, *args, **options):
        content_types = ContentType.objects.filter(app_label='hr')
        all_perms = Permission.objects.filter(content_type__in=content_types)

        # ─── Senior HR ─── full CRUD
        senior, created = Group.objects.get_or_create(name=SENIOR_HR_GROUP)
        senior.permissions.set(all_perms)
        self.stdout.write(f'{"Created" if created else "Updated"} group: {SENIOR_HR_GROUP}')

        # ─── Junior HR ─── view-only
        junior, created = Group.objects.get_or_create(name=JUNIOR_HR_GROUP)
        junior_perms = all_perms.filter(
            codename__startswith='view_'
        ) | all_perms.filter(
            codename='view_hr_section'
        )
        junior.permissions.set(junior_perms)
        self.stdout.write(f'{"Created" if created else "Updated"} group: {JUNIOR_HR_GROUP}')

        # ─── Legacy groups ─── ensure they exist (for backward compat)
        for legacy_name in LEGACY_SENIOR_GROUPS:
            grp, created = Group.objects.get_or_create(name=legacy_name)
            grp.permissions.set(all_perms)
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} legacy senior group: {legacy_name}')

        for legacy_name in LEGACY_JUNIOR_GROUPS:
            grp, created = Group.objects.get_or_create(name=legacy_name)
            grp.permissions.set(junior_perms)
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} legacy junior group: {legacy_name}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. senior_hr: {all_perms.count()} perms, '
            f'junior_hr: {junior_perms.count()} perms.'
        ))
