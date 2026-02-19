from django.db import migrations


HR_GROUP_NAMES = (
    'HR_MANAGER',
    'Senior Manager',
    'Junior Manager',
)


def create_hr_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    content_types = ContentType.objects.filter(app_label='hr')
    perms = Permission.objects.filter(content_type__in=content_types)

    for group_name in HR_GROUP_NAMES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(*perms)

    legacy_group = Group.objects.filter(name='HR_Manager').first()
    if legacy_group:
        hr_manager = Group.objects.filter(name='HR_MANAGER').first()
        if hr_manager:
            hr_manager.permissions.add(*legacy_group.permissions.all())
            hr_manager.user_set.add(*legacy_group.user_set.all())


def remove_hr_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=HR_GROUP_NAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0006_personnel_history'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_hr_role_groups, remove_hr_role_groups),
    ]
