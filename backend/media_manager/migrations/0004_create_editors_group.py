"""
Data migration: create the Editors group and assign media_manager permissions to it.
"""
from django.db import migrations


def create_editors_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    group, _ = Group.objects.get_or_create(name='Editors')

    # Permissions are created by Django's post_migrate signal; they may not
    # exist during initial migration. Use the management command
    # `setup_editors_group` after migrate to ensure permissions are assigned.
    media_models = ['news', 'contactrequest']
    for model_name in media_models:
        ct = ContentType.objects.filter(app_label='media_manager', model=model_name).first()
        if ct:
            perms = Permission.objects.filter(content_type=ct)
            group.permissions.add(*perms)


def remove_editors_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Editors').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('media_manager', '0003_move_profile_back_to_mainview'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_editors_group, remove_editors_group),
    ]
