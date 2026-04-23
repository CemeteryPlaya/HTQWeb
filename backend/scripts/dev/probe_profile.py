import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User

def probe_profile_me():
    client = APIClient()
    user = User.objects.get(username='Admin55')
    print(f"Authenticating as {user.username}...")
    client.force_authenticate(user=user)
    
    print("Probing /api/v1/profile/me/...")
    try:
        response = client.get('/api/v1/profile/me/')
        print(f"Status: {response.status_code}")
        if response.status_code == 500:
             print("Data:", response.data if hasattr(response, 'data') else "No data")
        else:
             print("Data (truncated):", str(response.data)[:200])
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_profile_me()
