from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tasks.models import Task, TaskLink

User = get_user_model()

class TaskLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_hr', password='123')
        self.task1 = Task.objects.create(summary="Task 1", reporter=self.user)
        self.task2 = Task.objects.create(summary="Task 2", reporter=self.user)
        self.task3 = Task.objects.create(summary="Task 3", reporter=self.user)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_basic_link(self):
        # Create blocks link
        response = self.client.post('/api/hr/task-links/', {
            'source': self.task1.id,
            'target': self.task2.id,
            'link_type': 'blocks'
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(TaskLink.objects.filter(source=self.task1, target=self.task2, link_type='blocks').exists())

    def test_prevent_self_reference(self):
        response = self.client.post('/api/hr/task-links/', {
            'source': self.task1.id,
            'target': self.task1.id,
            'link_type': 'blocks'
        })
        # Serializer / Model validation should block this
        self.assertEqual(response.status_code, 400)

    def test_prevent_cyclic_blocks_dependency(self):
        # 1 blocks 2
        TaskLink.objects.create(source=self.task1, target=self.task2, link_type='blocks')
        # 2 blocks 3
        TaskLink.objects.create(source=self.task2, target=self.task3, link_type='blocks')
        
        # Try to make 3 block 1 (Cycle: 1 -> 2 -> 3 -> 1)
        response = self.client.post('/api/hr/task-links/', {
            'source': self.task3.id,
            'target': self.task1.id,
            'link_type': 'blocks'
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Создание связи приведёт к циклической блокировке", str(response.data))
