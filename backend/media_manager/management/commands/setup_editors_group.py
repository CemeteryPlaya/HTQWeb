"""
Management command to set up the Editors group with media_manager permissions.

Usage:
    python manage.py setup_editors_group
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Create the Editors group and assign all media_manager permissions to it.'

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name='Editors')
        action = 'Created' if created else 'Found existing'
        self.stdout.write(f'{action} group: Editors')

        media_models = ['news', 'contactrequest']
        count = 0
        for model_name in media_models:
            ct = ContentType.objects.filter(app_label='media_manager', model=model_name).first()
            if ct:
                perms = Permission.objects.filter(content_type=ct)
                group.permissions.add(*perms)
                count += perms.count()

        self.stdout.write(self.style.SUCCESS(
            f'Assigned {count} permissions to Editors group.'
        ))
