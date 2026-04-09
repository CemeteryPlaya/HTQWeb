import threading
from django.test import TransactionTestCase
from tasks.models import Task, TaskSequence
from django.db import connection

class TaskKeyGenerationTests(TransactionTestCase):
    def test_sequential_keys(self):
        t1 = Task.objects.create(summary="T1", task_type='task', priority='medium')
        t2 = Task.objects.create(summary="T2", task_type='task', priority='medium')
        
        self.assertEqual(t1.key, 'TASK-1')
        self.assertEqual(t2.key, 'TASK-2')
        
    def test_concurrent_key_generation(self):
        if connection.vendor == 'sqlite':
            # SQLite does not support concurrent writes well with threading in tests
            # Skip this test for SQLite
            return

        def create_task(num):
            Task.objects.create(summary=f"Conn {num}", task_type='task', priority='medium')
            
        threads = []
        for i in range(10):
            t = threading.Thread(target=create_task, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.assertEqual(Task.objects.count(), 10)
        keys = set(Task.objects.values_list('key', flat=True))
        self.assertEqual(len(keys), 10)
        for i in range(1, 11):
            self.assertIn(f'TASK-{i}', keys)
