from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tasks.models import Task, Notification

User = get_user_model()

class NotificationTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(username='actor', password='123')
        self.assignee = User.objects.create_user(username='assignee', password='123')
        self.reporter = User.objects.create_user(username='reporter', password='123')
        
        # Actor needs permission to view/edit the task. Make actor the reporter.
        self.task = Task.objects.create(summary="Test Task", reporter=self.actor)
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.actor)

    def test_notification_on_assignee_change(self):
        # Update user assignee to the assignee user
        response = self.client.patch(f'/api/hr/tasks/{self.task.id}/', {
            'assignee': self.assignee.id
        })
        self.assertEqual(response.status_code, 200)
        
        # Check if notification was created for assignee
        notif = Notification.objects.filter(recipient=self.assignee).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.actor, self.actor)
        self.assertIn("назначил(а) эту задачу на вас", notif.verb)

    def test_notification_on_status_change(self):
        self.task.assignee = self.assignee
        self.task.save()
        
        # Status change
        response = self.client.patch(f'/api/hr/tasks/{self.task.id}/', {
            'status': 'in_progress'
        })
        self.assertEqual(response.status_code, 200)
        
        # Reporter (actor) and Assignee should receive it
        notifs = Notification.objects.filter(task=self.task)
        self.assertEqual(notifs.count(), 1) # Only assignee receives it because actor is the reporter
        recipients = [n.recipient for n in notifs]
        self.assertIn(self.assignee, recipients)

    def test_notification_on_new_comment(self):
        self.task.assignee = self.assignee
        self.task.save()
        
        # Add comment
        response = self.client.post(f'/api/hr/task-comments/', {
            'task': self.task.id,
            'body': 'A new observation.'
        })
        self.assertEqual(response.status_code, 201)
        
        notifs = Notification.objects.filter(verb__icontains="комментарий")
        self.assertEqual(notifs.count(), 1) # Only assignee receives it since reporter is the actor.
