"""
Create senior_hr and junior_hr groups with appropriate permissions.
Migrate legacy HR_MANAGER / Senior Manager users → senior_hr.
Migrate legacy Junior Manager users → junior_hr.
"""
from django.db import migrations


def create_rbac_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Collect all HR permissions
    hr_content_types = ContentType.objects.filter(app_label='hr')
    hr_permissions = Permission.objects.filter(content_type__in=hr_content_types)

    # ---- senior_hr ----
    senior_group, _ = Group.objects.get_or_create(name='senior_hr')
    senior_group.permissions.set(hr_permissions)

    # ---- junior_hr ----
    junior_group, _ = Group.objects.get_or_create(name='junior_hr')
    # Junior gets view + add + change, but NO delete
    junior_perms = hr_permissions.filter(codename__startswith='view_') | \
                   hr_permissions.filter(codename__startswith='add_') | \
                   hr_permissions.filter(codename__startswith='change_') | \
                   hr_permissions.filter(codename='view_hr_section')
    junior_group.permissions.set(junior_perms)

    # ---- Migrate legacy groups ----
    legacy_senior_names = ['HR_MANAGER', 'HR_Manager', 'Senior Manager']
    for legacy_name in legacy_senior_names:
        try:
            legacy_group = Group.objects.get(name=legacy_name)
            for user in legacy_group.user_set.all():
                user.groups.add(senior_group)
        except Group.DoesNotExist:
            pass

    try:
        junior_legacy = Group.objects.get(name='Junior Manager')
        for user in junior_legacy.user_set.all():
            user.groups.add(junior_group)
    except Group.DoesNotExist:
        pass


def reverse_rbac_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ('senior_hr', 'junior_hr'):
        Group.objects.filter(name=name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0008_rbac_soft_delete_financial_sro'),
        ('auth', '__latest__'),
        ('contenttypes', '__latest__'),
    ]

    operations = [
        migrations.RunPython(create_rbac_groups, reverse_rbac_groups),
    ]
