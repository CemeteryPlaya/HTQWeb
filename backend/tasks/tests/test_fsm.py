from django.test import TestCase
from django.contrib.auth import get_user_model
from tasks.models import Task
from tasks.serializers import TaskDetailSerializer

User = get_user_model()

class TaskFSMTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_hr', password='123')
        self.task = Task.objects.create(summary="Test FSM", status='open')

    def test_valid_transition(self):
        serializer = TaskDetailSerializer(
            instance=self.task, 
            data={'status': 'in_progress'}, 
            partial=True
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress')

    def test_invalid_transition(self):
        serializer = TaskDetailSerializer(
            instance=self.task, 
            data={'status': 'done'}, 
            partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("Недопустимый переход статуса: open -> done", str(serializer.errors))

    def test_same_status_transition(self):
        serializer = TaskDetailSerializer(
            instance=self.task, 
            data={'status': 'open'}, 
            partial=True
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
