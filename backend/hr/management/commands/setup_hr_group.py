"""
Management command to set up the HR_Manager group with all HR permissions.

Usage:
    python manage.py setup_hr_group
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Create the HR_Manager group and assign all hr.* permissions to it.'

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name='HR_Manager')
        action = 'Created' if created else 'Found existing'
        self.stdout.write(f'{action} group: HR_Manager')

        hr_models = [
            'department', 'position', 'employee',
            'vacancy', 'application', 'timetracking', 'document',
        ]

        count = 0
        for model_name in hr_models:
            ct = ContentType.objects.filter(app_label='hr', model=model_name).first()
            if ct:
                perms = Permission.objects.filter(content_type=ct)
                group.permissions.add(*perms)
                count += perms.count()

        self.stdout.write(self.style.SUCCESS(
            f'Assigned {count} permissions to HR_Manager group.'
        ))
