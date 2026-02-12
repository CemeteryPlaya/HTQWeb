from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Item
from .serializers import ItemSerializer
from media_manager.models import News
from .serializers import NewsSerializer

# Create your views here.
def index(request):
    return render(request, 'index.html')

class ItemViewSet(viewsets.ModelViewSet):
    # Берём все объекты Item
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    # Только авторизованные пользователи
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # При создании объекта автоматически подставляем текущего пользователя
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        # Пользователь видит только свои объекты
        if self.request.user.is_authenticated:
            return Item.objects.filter(owner=self.request.user)
        return Item.objects.none()


class IsAdminOrReadOnly(permissions.BasePermission):
    """Allow read-only access to anyone, but write access only to admin/staff users."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class NewsViewSet(viewsets.ModelViewSet):
    """API for news items. Readable by everyone; create/update/delete by admin/staff."""
    queryset = News.objects.all().order_by('-published_at', '-created_at')
    serializer_class = NewsSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'slug'
    pagination_class = None  # Disable pagination to return a simple array

    def get_queryset(self):
        # For anonymous / public users, only return published items
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_staff:
            return super().get_queryset()
        return News.objects.filter(published=True).order_by('-published_at', '-created_at')


# (removed NewsLastModifiedAPIView - polling endpoint no longer used)

from .models import Profile
from .serializers import ProfileSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for User Profiles.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        # Users can only see their own profile in this simplified version, 
        # or we could allow viewing others if requirements said so.
        # But requirement says "My Profile", so restricting to own for now safety.
        if self.request.user.is_authenticated:
            return Profile.objects.filter(user=self.request.user)
        return Profile.objects.none()

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Convenience endpoint to get/update the current user's profile.
        GET /api/v1/profile/me/
        """
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(profile, data=request.data, partial=(request.method == 'PATCH'))
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAdminUser
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, AdminUserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'put', 'patch', 'head', 'options']


from .serializers import ContactRequestSerializer
from media_manager.models import ContactRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import authentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action
from rest_framework.response import Response

@method_decorator(csrf_exempt, name='dispatch')
class ContactRequestViewSet(viewsets.ModelViewSet):
    """Endpoint for contact form submissions.

    - `create` is open to public (AllowAny)
    - listing / detail / update / delete require admin/staff
    """
    queryset = ContactRequest.objects.all().order_by('-created_at')
    serializer_class = ContactRequestSerializer
    pagination_class = None  # Disable pagination to return a simple array
    # Allow public creation without authentication so CSRF is not required for anonymous POSTs.
    # For other actions we must use the default authenticators so staff checks work.
    def get_authenticators(self):
        # When creating (public form submission) skip authenticators to avoid CSRF/session requirements.
        if getattr(self, 'action', None) == 'create':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        # For other actions require admin
        return [IsAdminUser()]

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def stats(self, request):
        """Return basic stats for admin UI: number of unhandled requests."""
        unhandled = ContactRequest.objects.filter(handled=False).count()
        return Response({"unhandled": unhandled})

    def perform_create(self, serializer):
        # Save the contact request first
        instance = serializer.save()

        # Prepare email details
        subject = f"New Contact Request from {instance.first_name} {instance.last_name}"
        message = (
            f"You have received a new contact request:\n\n"
            f"Name: {instance.first_name} {instance.last_name}\n"
            f"Email: {instance.email}\n"
            f"Message: {instance.message}\n\n"
            f"You can manage this request in the admin panel."
        )
        recipient_list = getattr(settings, 'STAFF_NOTIFICATION_EMAILS', [])

        if recipient_list:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=True,
                )
            except Exception as e:
                # We fail silently by default in send_mail, but we can log here if needed
                print(f"Error sending email: {e}")
