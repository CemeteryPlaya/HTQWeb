import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User

def probe_admin_users():
    client = APIClient()
    user = User.objects.get(username='Endmin')
    print(f"Authenticating as {user.username}...")
    client.force_authenticate(user=user)
    
    print("Probing /api/v1/admin/users/...")
    try:
        response = client.get('/api/v1/admin/users/')
        print(f"Status: {response.status_code}")
        if isinstance(response.data, dict) and 'results' in response.data:
             print(f"Data count: {response.data.get('count')}")
             print(f"Results: {len(response.data['results'])} items on this page")
        elif isinstance(response.data, list):
             print("Data count:", len(response.data))
        else:
             print("Data:", response.data)
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_admin_users()
