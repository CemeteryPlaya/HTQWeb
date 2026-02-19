from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import Item

class ContentApiTestCase(APITestCase):
    def setUp(self):
        # Создаём пользователя
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpassword',
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
        )
        self.item = Item.objects.create(title="Test Item", owner=self.user)
        
        # Получаем JWT токен
        url = reverse('token_obtain_pair')
        data = {'email': 'testuser@example.com', 'password': 'testpassword'}
        response = self.client.post(url, data, format='json')
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_get_items(self):
        """Тест получения списка объектов"""
        url = reverse('item-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
        else:
            self.assertEqual(len(response.data), 1)

    def test_create_item(self):
        """Тест создания объекта"""
        url = reverse('item-list')
        data = {'title': 'New Item', 'description': 'Desc'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Item.objects.count(), 2)
        self.assertEqual(Item.objects.get(id=response.data['id']).owner, self.user)

    def test_delete_item(self):
        """Тест удаления объекта"""
        url = reverse('item-detail', args=[self.item.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Item.objects.count(), 0)

    def test_unauthorized(self):
        """Тест доступа без токена"""
        self.client.credentials() # Сбрасываем токен
        url = reverse('item-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


from .models import Profile

class ProfileTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='profileuser@example.com',
            password='password123',
            email='test@example.com',
            first_name='Test',
            last_name='User',
        )
        self.client.force_authenticate(user=self.user)
        self.profile_url = '/api/v1/profile/me/'

    def test_profile_created_signal(self):
        """Test that profile is automatically created when user is created"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.user, self.user)

    def test_get_profile_authorized(self):
        """Test that authenticated user can access their profile"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['firstName'], 'Test')

    def test_update_profile(self):
        """Test updating profile fields"""
        data = {
            'display_name': 'New Display Name',
            'bio': 'New Bio'
        }
        response = self.client.patch(self.profile_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, 'New Display Name')
        self.assertEqual(self.user.profile.bio, 'New Bio')

    def test_update_settings(self):
        """Test updating JSON settings"""
        data = {
            'settings': {'theme': 'dark', 'notifications': True}
        }
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.settings, {'theme': 'dark', 'notifications': True})
