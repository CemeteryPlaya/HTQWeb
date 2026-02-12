"""
Data migration: create the HR_Manager group and assign all hr.* permissions to it.
"""
from django.db import migrations


def create_hr_manager_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    group, _ = Group.objects.get_or_create(name='HR_Manager')

    # Collect all permissions for models defined in the hr app.
    # Note: permissions are populated by Django's post_migrate signal,
    # so they may not exist yet during initial migration. The management
    # command `setup_hr_group` can be used to assign them after migrate.
    hr_models = [
        'department', 'position', 'employee',
        'vacancy', 'application', 'timetracking', 'document',
    ]
    for model_name in hr_models:
        ct = ContentType.objects.filter(app_label='hr', model=model_name).first()
        if ct:
            perms = Permission.objects.filter(content_type=ct)
            group.permissions.add(*perms)


def remove_hr_manager_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='HR_Manager').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_hr_manager_group, remove_hr_manager_group),
    ]
