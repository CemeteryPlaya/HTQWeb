"""
URL configuration for HTQWeb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mainView.views import ItemViewSet, index, ProfileViewSet, RegisterView, AdminUserViewSet
from mainView.views import NewsViewSet, ContactRequestViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'items', ItemViewSet, basename='item')
router.register(r'news', NewsViewSet, basename='news')
router.register(r'v1/profile', ProfileViewSet, basename='profile')
router.register(r'v1/admin/users', AdminUserViewSet, basename='admin_users')
router.register(r'v1/contact-requests', ContactRequestViewSet, basename='contact_requests')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/hr/', include('hr.urls', namespace='hr')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/register/', RegisterView.as_view(), name='auth_register'),
    path('', index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
