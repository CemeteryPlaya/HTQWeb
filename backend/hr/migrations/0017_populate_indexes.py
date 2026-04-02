"""
Data migration: populate `index` for existing Department and Position rows.
"""
from django.db import migrations


def populate_indexes(apps, schema_editor):
    Department = apps.get_model('hr', 'Department')
    Position = apps.get_model('hr', 'Position')

    # Assign sequential indexes to departments (ordered by name)
    for i, dept in enumerate(Department.objects.order_by('name'), start=1):
        dept.index = i
        dept.save(update_fields=['index'])

    # Assign hierarchical indexes to positions (dept_index.N)
    for dept in Department.objects.order_by('index'):
        positions = Position.objects.filter(department=dept).order_by('title')
        for j, pos in enumerate(positions, start=1):
            pos.index = f'{dept.index}.{j}'
            pos.save(update_fields=['index'])

    # Handle orphan positions (no department)
    orphans = Position.objects.filter(department__isnull=True, index__isnull=True).order_by('title')
    for k, pos in enumerate(orphans, start=1):
        pos.index = f'0.{k}'
        pos.save(update_fields=['index'])


def reverse_indexes(apps, schema_editor):
    Department = apps.get_model('hr', 'Department')
    Position = apps.get_model('hr', 'Position')
    Department.objects.update(index=None)
    Position.objects.update(index=None)


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0016_department_position_index'),
    ]

    operations = [
        migrations.RunPython(populate_indexes, reverse_indexes),
    ]
