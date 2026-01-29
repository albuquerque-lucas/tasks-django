from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Task

User = get_user_model()


class TaskTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_task(self):
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            description='A test task'
        )
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, 'created')


