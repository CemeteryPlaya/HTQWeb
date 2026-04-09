from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from urllib.parse import urlparse, urlunparse
import ipaddress
import json
import logging
from rest_framework import viewsets, permissions, exceptions as drf_exceptions, status as drf_status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Item
from .serializers import ItemSerializer, EmailTokenObtainPairSerializer
from media_manager.models import News
from .serializers import NewsSerializer
from hr.roles import has_hr_group

logger = logging.getLogger(__name__)

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None
# Create your views here.
def index(request):
    return render(request, 'index.html')


class SafeTokenObtainPairView(TokenObtainPairView):
    """
    JWT-токен с глобальным перехватчиком исключений.

    Стандартный TokenObtainPairView «падает» с 500 при любой необработанной
    ошибке (ошибка БД, неверный CSRF, ошибка конфигурации). Это вызывает
    каскад 401-циклов на фронтенде: клиент не может получить токен, но
    старый refresh-токен ещё есть — и начинает бесконечно пытаться его обновить.

    Данный класс гарантирует, что эндпоинт всегда возвращает структурированный
    JSON (никогда HTML-страницу Django debug или пустое тело 500).
    """

    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except drf_exceptions.AuthenticationFailed as exc:
            # Уже сформированный DRF-ответ — просто проброс без изменений.
            return Response(
                {'detail': exc.detail, 'code': getattr(exc, 'default_code', 'authentication_failed')},
                status=drf_status.HTTP_401_UNAUTHORIZED,
            )
        except drf_exceptions.ValidationError as exc:
            return Response(
                {'detail': exc.detail, 'code': 'validation_error'},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            # Неожиданная ошибка (БД, конфигурация и т.д.) — логируем полный traceback
            # и возвращаем 422, а НЕ 500, чтобы фронтенд не запускал цикл обновления токена.
            logger.exception('Unexpected error in SafeTokenObtainPairView')
            return Response(
                {
                    'detail': 'Ошибка сервера при аутентификации. Попробуйте позже.',
                    'code': 'server_error',
                },
                status=drf_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


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
    """Allow read-only access to anyone, but write access only to admin/staff/Editors users."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff:
            return True
        return request.user.groups.filter(name='Editors').exists()


class NewsViewSet(viewsets.ModelViewSet):
    """API for news items. Readable by everyone; create/update/delete by admin/staff."""
    queryset = News.objects.all().order_by('-published_at', '-created_at')
    serializer_class = NewsSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'slug'
    pagination_class = None  # Disable pagination to return a simple array

    def get_queryset(self):
        # For staff users or Editors group members, return all items (including unpublished)
        if self.request.user and self.request.user.is_authenticated:
            if self.request.user.is_staff or self.request.user.groups.filter(name='Editors').exists():
                return super().get_queryset()
        return News.objects.filter(published=True).order_by('-published_at', '-created_at')

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.AllowAny])
    def translate(self, request, slug=None):
        """
        Dynamically translates a news article's title and content to the target language 
        (defaulting to English) using deep-translator.
        """
        if not GoogleTranslator:
            from rest_framework.response import Response
            return Response({"error": "Translation service is not configured."}, status=503)

        news = self.get_object()
        
        if request.method == 'GET':
            target_lang = request.query_params.get('target', 'en')
        else:
            target_lang = request.data.get('target', 'en')

        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated_title = translator.translate(news.title) if news.title else ""
            
            # Translate content or summary
            content_to_translate = news.content if news.content else (news.summary or "")
            translated_content = translator.translate(content_to_translate) if content_to_translate else ""
            
            from rest_framework.response import Response
            return Response({
                "source_slug": news.slug,
                "target_language": target_lang,
                "translated_title": translated_title,
                "translated_content": translated_content
            })
        except Exception as e:
            import logging
            logger = logging.getLogger('mainView')
            logger.error("Translation error for news %s: %s", news.slug, str(e))
            from rest_framework.response import Response
            return Response({"error": "Failed to translate article."}, status=500)


# (removed NewsLastModifiedAPIView - polling endpoint no longer used)

from .models import Profile
from .serializers import ProfileSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for User Profiles.
    Regular users can only see/edit their own profile via /me/.
    HR Managers and staff can list and edit all profiles.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    pagination_class = None

    def _is_hr_or_staff(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return True
        return has_hr_group(user)

    def get_queryset(self):
        if self._is_hr_or_staff():
            return Profile.objects.select_related('user').all().order_by('user__first_name', 'user__last_name')
        if self.request.user.is_authenticated:
            return Profile.objects.filter(user=self.request.user)
        return Profile.objects.none()

    @action(detail=False, methods=['post'], url_path='change-password', permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """
        Endpoint for user to change their own password, primarily to clear the must_change_password flag.
        """
        user = request.user
        new_password = request.data.get('new_password')
        if not new_password:
            return Response({"detail": "new_password is required"}, status=400)
            
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        if hasattr(user, 'profile'):
            user.profile.must_change_password = False
            user.profile.save(update_fields=['must_change_password'])
            
        return Response({"detail": "Password changed successfully"})

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


class PendingRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """List users awaiting approval (is_active=False) and approve/reject them."""
    from .serializers import PendingUserSerializer
    serializer_class = PendingUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        return User.objects.filter(is_active=False).order_by('-date_joined')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'status': 'approved', 'username': user.username})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        user = self.get_object()
        username = user.username
        user.delete()
        return Response({'status': 'rejected', 'username': username})


from .serializers import ContactRequestSerializer
from media_manager.models import ContactRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import authentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action
from rest_framework.response import Response

class IsAdminOrEditors(permissions.BasePermission):
    """Allow access to admin/staff users or members of the Editors group."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_staff:
            return True
        return request.user.groups.filter(name='Editors').exists()

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
        # For other actions require admin or Editors group
        return [IsAdminOrEditors()]

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrEditors])
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


class ConferenceConfigView(APIView):
    """Return conference runtime config (backend is the single source of truth)."""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _normalize_signaling_path(raw_path: str) -> str:
        path = (raw_path or '/ws/sfu/').strip() or '/ws/sfu/'
        return path if path.startswith('/') else f'/{path}'

    @staticmethod
    def _is_local_or_private_host(hostname: str) -> bool:
        normalized = (hostname or '').strip().lower()
        if not normalized:
            return True

        if normalized in {'localhost', '::1'} or normalized.endswith('.localhost'):
            return True

        try:
            ip = ipaddress.ip_address(normalized)
            return ip.is_loopback or ip.is_private or ip.is_link_local
        except ValueError:
            return False

    def _resolve_signaling_url(self, request) -> str:
        raw_url = (settings.CONFERENCE_SFU_URL or '').strip()
        signaling_path = self._normalize_signaling_path(settings.CONFERENCE_SFU_PATH)
        if not raw_url:
            return ''

        try:
            parsed = urlparse(raw_url)
        except ValueError:
            return ''

        scheme = (parsed.scheme or '').lower()
        if scheme == 'http':
            scheme = 'ws'
        elif scheme == 'https':
            scheme = 'wss'
        elif scheme not in {'ws', 'wss'}:
            return ''

        request_host = request.get_host().split(':', 1)[0]
        target_host = (parsed.hostname or '').strip()
        if (
            target_host
            and not self._is_local_or_private_host(request_host)
            and self._is_local_or_private_host(target_host)
        ):
            return ''

        path = parsed.path or ''
        if not path or path == '/':
            path = signaling_path

        if request.is_secure() and scheme == 'ws':
            scheme = 'wss'

        normalized = parsed._replace(scheme=scheme, path=path)
        return urlunparse(normalized)

    @staticmethod
    def _resolve_ice_servers() -> list[dict]:
        raw = (getattr(settings, 'CONFERENCE_ICE_SERVERS', '') or '').strip()
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return []

        if not isinstance(parsed, list):
            return []

        normalized: list[dict] = []
        for entry in parsed:
            if not isinstance(entry, dict):
                continue

            raw_urls = entry.get('urls')
            if isinstance(raw_urls, str):
                urls = [raw_urls.strip()] if raw_urls.strip() else []
            elif isinstance(raw_urls, list):
                urls = [
                    str(url).strip()
                    for url in raw_urls
                    if isinstance(url, str) and str(url).strip()
                ]
            else:
                urls = []

            if not urls:
                continue

            server: dict = {"urls": urls if len(urls) > 1 else urls[0]}
            username = entry.get('username')
            credential = entry.get('credential')
            if isinstance(username, str) and username.strip():
                server['username'] = username.strip()
            if isinstance(credential, str) and credential.strip():
                server['credential'] = credential.strip()

            normalized.append(server)

        return normalized

    def get(self, request):
        return Response({
            "sfu_signaling_url": self._resolve_signaling_url(request),
            "sfu_signaling_path": settings.CONFERENCE_SFU_PATH,
            "ice_servers": self._resolve_ice_servers(),
        })
