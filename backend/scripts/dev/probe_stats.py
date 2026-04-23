import os
import sys
import django

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User

def probe_stats():
    client = APIClient()
    user = User.objects.get(username='Admin55')
    print(f"Authenticating as {user.username}...")
    client.force_authenticate(user=user)
    
    print("Probing /api/v1/contact-requests/stats/...")
    try:
        response = client.get('/api/v1/contact-requests/stats/')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_stats()
