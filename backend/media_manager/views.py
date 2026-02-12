import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import News, ContactRequest
from .serializers import NewsSerializer, ContactRequestSerializer

logger = logging.getLogger('media_manager')


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
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'slug'
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        is_staff = user and user.is_authenticated and user.is_staff
        qs = super().get_queryset() if is_staff else News.objects.filter(published=True).order_by('-published_at', '-created_at')
        logger.info('[NewsViewSet.get_queryset] user=%s is_staff=%s action=%s count=%d items=%s',
                     getattr(user, 'username', 'anon'), is_staff, self.action,
                     qs.count(), list(qs.values_list('slug', 'published')))
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info('[NewsViewSet.perform_create] slug=%s published=%s published_at=%s',
                     instance.slug, instance.published, instance.published_at)
        if instance.published and not instance.published_at:
            instance.published_at = timezone.now()
            instance.save(update_fields=['published_at'])
        elif not instance.published and instance.published_at:
            instance.published_at = None
            instance.save(update_fields=['published_at'])

    def perform_update(self, serializer):
        old_published = serializer.instance.published if serializer.instance else None
        instance = serializer.save()
        logger.info('[NewsViewSet.perform_update] slug=%s old_published=%s new_published=%s published_at=%s',
                     instance.slug, old_published, instance.published, instance.published_at)
        if instance.published and not instance.published_at:
            instance.published_at = timezone.now()
            instance.save(update_fields=['published_at'])
        elif not instance.published and instance.published_at:
            instance.published_at = None
            instance.save(update_fields=['published_at'])


@method_decorator(csrf_exempt, name='dispatch')
class ContactRequestViewSet(viewsets.ModelViewSet):
    """Endpoint for contact form submissions.

    - ``create`` is open to public (AllowAny)
    - listing / detail / update / delete require admin/staff
    """
    queryset = ContactRequest.objects.select_related('replied_by').all().order_by('-created_at')
    serializer_class = ContactRequestSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_authenticators(self):
        if getattr(self, 'action', None) == 'create':
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def stats(self, request):
        """Return basic stats for admin UI: number of unhandled requests."""
        unhandled = ContactRequest.objects.filter(handled=False).count()
        return Response({"unhandled": unhandled})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reply(self, request, pk=None):
        """Send a reply to a contact request and store the response."""
        instance = self.get_object()
        reply_message = (request.data.get('reply_message') or '').strip()
        if not reply_message:
            return Response({"detail": "reply_message is required"}, status=400)

        instance.reply_message = reply_message
        instance.replied_at = timezone.now()
        instance.replied_by = request.user
        instance.handled = True
        instance.save(update_fields=['reply_message', 'replied_at', 'replied_by', 'handled'])

        subject = "Reply to your contact request"
        message = (
            "Hello,\n\n"
            "We have responded to your contact request:\n\n"
            f"{reply_message}\n\n"
            "Best regards,\nHi-Tech Group"
        )

        try:
            send_mail(
                subject, message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error("Error sending reply email: %s", e)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        instance = serializer.save()

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
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=True,
                )
            except Exception as e:
                logger.error("Error sending email: %s", e)

