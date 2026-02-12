from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from mainView.models import Profile

class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com', first_name='Test', last_name='User')
        self.client = APIClient()
        self.profile_url = '/api/v1/profile/me/'

    def test_profile_created_signal(self):
        """Test that profile is automatically created when user is created"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.user, self.user)

    def test_get_profile_unauthorized(self):
        """Test that unauthenticated user cannot access profile"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_authorized(self):
        """Test that authenticated user can access their profile"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['firstName'], 'Test')

    def test_update_profile(self):
        """Test updating profile fields"""
        self.client.force_authenticate(user=self.user)
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
        self.client.force_authenticate(user=self.user)
        data = {
            'settings': {'theme': 'dark', 'notifications': True}
        }
        # JSON field update via PATCH needs careful handling in DRF if partial, 
        # but here we send the full settings object replacement usually, 
        # or we might expect merge. Standard DRF replaces the field value.
        import json
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.settings, {'theme': 'dark', 'notifications': True})
