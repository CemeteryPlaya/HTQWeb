import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User

def probe_token():
    client = APIClient()
    # Assume Admin55 password is same as username or unknown.
    # We don't need real password if we just want to see if the view crashes BEFORE authentication check,
    # or we can try to guess or use another user.
    
    # Actually, TokenObtainPairView only crashes AFTER valid authentication if it's the signal,
    # OR if it's the serializer setup.
    
    print("Probing /api/token/ with invalid credentials to see if it even responds (should be 401, not 500)...")
    try:
        response = client.post('/api/token/', {'username': 'Admin55', 'password': 'wrongpassword'})
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_token()
