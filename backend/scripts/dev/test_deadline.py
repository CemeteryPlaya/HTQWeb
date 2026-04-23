import os
import django
import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from tasks.models import Task, ProductionDay
from django.contrib.auth import get_user_model

User = get_user_model()

def sync_sequence():
    from django.db.models import Max
    import re
    max_key = Task.objects.aggregate(Max('key'))['key__max']
    if max_key:
        match = re.search(r'TASK-(\d+)', max_key)
        if match:
            max_val = int(match.group(1))
            from tasks.models import TaskSequence
            seq, _ = TaskSequence.objects.get_or_create(project_prefix='TASK')
            if seq.last_value < max_val:
                seq.last_value = max_val
                seq.save()
                print(f"Synced TaskSequence to {max_val}")

def test_deadline_calculation():
    sync_sequence()
    user = User.objects.first()
    if not user:
        print("No user found in DB. Please create a user first.")
        return

    # 2025-03-14 is a Friday (Weekday 4)
    # 2025-03-15 is a Saturday
    # 2025-03-16 is a Sunday
    # 2025-03-17 is a Monday
    
    start_date = datetime.date(2025, 3, 14)
    estimated_days = 2
    
    print(f"Testing deadline for start_date={start_date}, estimated_days={estimated_days}")
    
    # Create task
    task = Task.objects.create(
        summary="Test O(1) Deadline",
        reporter=user,
        start_date=start_date,
        estimated_working_days=estimated_days
    )
    
    print(f"Task created: {task.key}")
    print(f"Calculated due_date: {task.due_date}")
    
    # Expected: 
    # Day 1: Friday (Mar 14)
    # Day 2: Monday (Mar 17) -> Target
    expected_date = datetime.date(2025, 3, 17)
    
    if task.due_date == expected_date:
        print("✅ SUCCESS: Deadline correctly calculated (skipped weekend).")
    else:
        print(f"❌ FAILURE: Expected {expected_date}, got {task.due_date}")

    # Test shifting
    print("\nTesting update of estimated days...")
    task.estimated_working_days = 5
    task.save()
    print(f"New due_date: {task.due_date}")
    # Fri (1), Mon (2), Tue (3), Wed (4), Thu (5 -> Mar 20)
    expected_date_2 = datetime.date(2025, 3, 20)
    if task.due_date == expected_date_2:
        print("✅ SUCCESS: Deadline correctly updated.")
    else:
        print(f"❌ FAILURE: Expected {expected_date_2}, got {task.due_date}")

if __name__ == "__main__":
    test_deadline_calculation()
