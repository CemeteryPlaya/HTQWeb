from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tasks.models import Task
from tasks.serializers import TaskDetailSerializer, TaskListSerializer

User = get_user_model()

class DateRollupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_rollup', password='123')
        
        # Create an Epic
        self.epic = Task.objects.create(
            summary="Main Epic", 
            task_type='epic',
            reporter=self.user,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=10)
        )
        
        # Create Subtasks
        self.sub1 = Task.objects.create(
            summary="Subtask 1", 
            task_type='subtask', 
            parent=self.epic,
            reporter=self.user,
            start_date=date.today() - timedelta(days=2), # Earlier than epic
            due_date=date.today() + timedelta(days=5)
        )
        
        self.sub2 = Task.objects.create(
            summary="Subtask 2", 
            task_type='subtask', 
            parent=self.epic,
            reporter=self.user,
            start_date=date.today() + timedelta(days=2),
            due_date=date.today() + timedelta(days=15) # Later than epic -> Warning expected
        )

    def test_epic_effective_dates(self):
        # Serialize Epic
        serializer = TaskDetailSerializer(instance=self.epic)
        data = serializer.data
        
        # Effective start date should be min(epic.start_date, subtasks.start_date) = sub1 start_date
        self.assertEqual(data['effective_start_date'], self.sub1.start_date)
        
        # Effective due date should be max(epic.due_date, subtasks.due_date) = sub2 due_date
        self.assertEqual(data['effective_due_date'], self.sub2.due_date)
        
    def test_subtask_date_warnings(self):
        # Serialize Subtask 2 (due date exceeds parent Epic due date)
        serializer = TaskDetailSerializer(instance=self.sub2)
        data = serializer.data
        
        # Should have exactly 1 warning about date conflict
        warnings = data.get('date_warnings', [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]['code'], 'date_conflict')
        self.assertIn('Срок подзадачи выходит за рамки родительского эпика', warnings[0]['message'])

    def test_subtask_no_date_warnings(self):
        # Serialize Subtask 1 (within parent dates)
        serializer = TaskDetailSerializer(instance=self.sub1)
        data = serializer.data
        
        warnings = data.get('date_warnings', [])
        self.assertEqual(len(warnings), 0)

    def test_project_version_effective_date(self):
        from tasks.models import ProjectVersion
        from tasks.serializers import ProjectVersionSerializer
        
        version = ProjectVersion.objects.create(
            name="v1.0",
            status="planned",
            release_date=date.today() + timedelta(days=20)
        )
        
        # Assign tasks to version
        self.epic.version = version
        self.epic.save()
        
        # Create a task exceeding version release date
        Task.objects.create(
            summary="Late Task", 
            task_type='task',
            reporter=self.user,
            version=version,
            due_date=date.today() + timedelta(days=30)
        )
        
        serializer = ProjectVersionSerializer(instance=version)
        data = serializer.data
        
        # Should be max(tasks due_dates) -> today + 30
        self.assertEqual(data['effective_release_date'], date.today() + timedelta(days=30))

