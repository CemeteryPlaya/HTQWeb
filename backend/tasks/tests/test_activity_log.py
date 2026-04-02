from django.test import TestCase
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from tasks.models import Task, TaskActivity
from tasks.serializers import TaskDetailSerializer

User = get_user_model()

class TaskActivityLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_hr', password='123')
        self.task = Task.objects.create(summary="Original Summary", description="Orig Desc", status='open')
        self.factory = APIRequestFactory()

    def test_activity_logged_on_update(self):
        request = self.factory.patch('/')
        request.user = self.user
        
        serializer = TaskDetailSerializer(
            instance=self.task, 
            data={'summary': 'New Summary', 'status': 'in_progress'}, 
            partial=True,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        
        activities = TaskActivity.objects.filter(task=self.task)
        self.assertEqual(activities.count(), 2)
        
        summary_log = activities.get(field_name='summary')
        self.assertEqual(summary_log.old_value, 'Original Summary')
        self.assertEqual(summary_log.new_value, 'New Summary')
        self.assertEqual(summary_log.actor, self.user)
        
        status_log = activities.get(field_name='status')
        self.assertEqual(status_log.old_value, 'open')
        self.assertEqual(status_log.new_value, 'in_progress')

    def test_no_activity_logged_if_no_changes(self):
        request = self.factory.patch('/')
        request.user = self.user
        
        serializer = TaskDetailSerializer(
            instance=self.task, 
            data={'summary': 'Original Summary'}, 
            partial=True,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        
        activities = TaskActivity.objects.filter(task=self.task)
        self.assertEqual(activities.count(), 0)
