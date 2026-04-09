"""
Data migration: copy Employee.phone → Profile.phone for each linked user.
"""
from django.db import migrations


def migrate_phone_forward(apps, schema_editor):
    Employee = apps.get_model('hr', 'Employee')
    Profile = apps.get_model('mainView', 'Profile')

    for emp in Employee.objects.filter(phone__gt='').select_related('user'):
        try:
            profile = Profile.objects.get(user=emp.user)
            if not profile.phone:  # don't overwrite if Profile already has a phone
                profile.phone = emp.phone
                profile.save(update_fields=['phone'])
        except Profile.DoesNotExist:
            pass


def migrate_phone_backward(apps, schema_editor):
    Employee = apps.get_model('hr', 'Employee')
    Profile = apps.get_model('mainView', 'Profile')

    for profile in Profile.objects.filter(phone__gt='').select_related('user'):
        try:
            emp = Employee.objects.get(user=profile.user)
            if not emp.phone:
                emp.phone = profile.phone
                emp.save(update_fields=['phone'])
        except Employee.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0013_remove_task_models'),
        ('mainView', '0012_profile_phone'),
    ]

    operations = [
        migrations.RunPython(migrate_phone_forward, migrate_phone_backward),
    ]
