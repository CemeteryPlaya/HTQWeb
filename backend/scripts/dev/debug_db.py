import os
import django
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HTQWeb.settings")
django.setup()

from django.contrib.auth.models import User
from hr.models import Employee

with open('debug_output_utf8.txt', 'w', encoding='utf-8') as f:
    for u in User.objects.all():
        f.write(f"User: {u.username}, Staff: {u.is_staff}, ID: {u.id}\n")
        try:
            f.write(f"  Groups: {[g.name for g in u.groups.all()]}\n")
        except Exception as e:
            f.write(f"  Groups Error: {e}\n")
        
        try:
            emp = Employee.objects.get(user=u)
            f.write(f"  Employee Dept: {emp.department.name if emp.department else 'None'}\n")
        except Exception as e:
            f.write(f"  No Employee Record: {e}\n")

        try:
            f.write(f"  Profile Dept obj: {getattr(u.profile, 'department', 'No Profile attr')}\n")
            roles = ['user']
            if u.is_staff: roles.append('staff')
            for name in u.groups.values_list('name', flat=True):
                roles.append(name.lower().replace(' ', '_').replace('-', '_'))
            f.write(f"  Profile roles: {roles}\n")
        except Exception as e:
            f.write(f"  Profile Error: {e}\n")
        f.write("-" * 20 + "\n")
