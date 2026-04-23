import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User

def debug_request():
    client = APIClient()
    user = User.objects.filter(is_staff=True).first()
    if not user:
        print("No staff user found to authenticate.")
        return
    
    print(f"Authenticating as user: {user.username}")
    client.force_authenticate(user=user)
    
    urls = ['/api/v1/contact-requests/', '/api/v1/profile/me/']
    
    for url in urls:
        print(f"\nProbing URL: {url}")
        try:
            response = client.get(url)
            print(f"Status: {response.status_code}")
            if response.status_code == 500:
                print("Error data:", response.data if hasattr(response, 'data') else "No data")
            else:
                print("Response data (truncated):", str(response.data)[:200])
        except Exception as e:
            print(f"Exception during request to {url}:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_request()
