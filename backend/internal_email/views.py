from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import EmailMessage, EmailRecipientStatus, EmailAttachment
from .serializers import EmailMessageSerializer, EmailRecipientStatusSerializer
from .services import EmailService

User = get_user_model()


class InboxView(generics.ListAPIView):
    serializer_class = EmailRecipientStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmailRecipientStatus.objects.filter(
            user=self.request.user, 
            folder=EmailRecipientStatus.Folder.INBOX
        ).select_related('message', 'user').order_by('-message__created_at')


class SentView(generics.ListAPIView):
    serializer_class = EmailMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmailMessage.objects.filter(
            sender=self.request.user, 
            is_draft=False
        ).prefetch_related('recipient_statuses').order_by('-sent_at')


class DraftsView(generics.ListAPIView):
    serializer_class = EmailMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmailMessage.objects.filter(
            sender=self.request.user, 
            is_draft=True
        ).order_by('-created_at')


class TrashView(generics.ListAPIView):
    serializer_class = EmailRecipientStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmailRecipientStatus.objects.filter(
            user=self.request.user, 
            folder=EmailRecipientStatus.Folder.TRASH
        ).select_related('message', 'user').order_by('-message__created_at')


class EmailSendView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        # Extract inputs
        subject = request.data.get('subject', '')
        body = request.data.get('body', '')
        recipient_ids = request.data.get('recipients', [])
        external_emails = request.data.get('external_recipients', [])

        # FormData often sends lists as individual items or JSON strings
        if isinstance(recipient_ids, str):
            try:
                import json
                recipient_ids = json.loads(recipient_ids)
            except (ValueError, TypeError):
                # Fallback: maybe it's just a single ID or a comma-separated list? 
                # But typically we expect a JSON array from our frontend FormData logic.
                pass
                
        if isinstance(external_emails, str):
            try:
                import json
                external_emails = json.loads(external_emails)
            except (ValueError, TypeError):
                pass

        # Validate subject and body using serializer
        input_serializer = EmailMessageSerializer(data={
            'subject': subject,
            'body': body
        })

        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_subject = input_serializer.validated_data.get('subject', '')
        validated_body = input_serializer.validated_data.get('body', '')

        valid_external = []
        if external_emails and isinstance(external_emails, list):
            for email in external_emails:
                try:
                    validate_email(email)
                    valid_external.append(email)
                except ValidationError:
                    return Response({'error': f'Некорректный email адрес: {email}'}, status=status.HTTP_400_BAD_REQUEST)

        valid_internal = []
        if recipient_ids and isinstance(recipient_ids, list) and len(recipient_ids) > 0:
            valid_internal = User.objects.filter(id__in=recipient_ids)
            if not valid_internal.exists():
                 return Response({'error': 'Ни один из указанных внутренних получателей не существует.'}, status=status.HTTP_400_BAD_REQUEST)

        if not valid_internal and not valid_external:
            return Response({'error': 'Укажите хотя бы одного внутреннего или внешнего получателя.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract files from request.FILES
        attachments = request.FILES.getlist('attachments')
        
        # Delegate to service layer
        message = EmailService.send_email(
            sender=request.user,
            subject=validated_subject,
            body=validated_body,
            recipients=valid_internal,
            attachments=attachments,
            external_recipients=valid_external
        )

        serializer = EmailMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EmailDraftView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        subject = request.data.get('subject', '')
        body = request.data.get('body', '')
        external_emails = request.data.get('external_recipients', [])

        if isinstance(external_emails, str):
            try:
                import json
                external_emails = json.loads(external_emails)
            except (ValueError, TypeError):
                pass
                
        valid_external = []
        if external_emails and isinstance(external_emails, list):
            for email in external_emails:
                try:
                    validate_email(email)
                    valid_external.append(email)
                except ValidationError:
                    return Response({'error': f'Некорректный email адрес: {email}'}, status=status.HTTP_400_BAD_REQUEST)

        # Pass data through the serializer for Bleach and CRLF sanitization
        input_serializer = EmailMessageSerializer(data={
            'subject': subject,
            'body': body
        })

        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_subject = input_serializer.validated_data.get('subject', '')
        validated_body = input_serializer.validated_data.get('body', '')

        # Since it's a draft, no recipients are currently created and no service transaction is explicitly needed yet
        message = EmailMessage.objects.create(
            sender=request.user,
            subject=validated_subject,
            body=validated_body,
            is_draft=True,
            external_recipients=valid_external
        )

        serializer = EmailMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EmailReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        status_obj = get_object_or_404(EmailRecipientStatus, pk=pk, user=request.user)
        is_read = request.data.get('is_read', True)
        
        status_obj.is_read = is_read
        if is_read and not status_obj.read_at:
            status_obj.read_at = timezone.now()
        status_obj.save()

        serializer = EmailRecipientStatusSerializer(status_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════════════
#  OAuth 2.0 endpoints
# ═══════════════════════════════════════════════════════════════════════════
import secrets
from datetime import timedelta as td
from .models import EmailOAuthToken
from .oauth import (
    get_google_auth_url, exchange_google_code, get_google_user_email,
    get_microsoft_auth_url, exchange_microsoft_code, get_microsoft_user_email,
    GOOGLE_SCOPES, MICROSOFT_SCOPES,
)


class OAuthInitView(APIView):
    """
    GET /api/email/oauth/init/?provider=google|microsoft
    Generates a CSRF-safe state token, stores it in session, and returns
    the provider's authorization URL for the frontend to redirect to.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = request.query_params.get('provider', '').lower()
        if provider not in ('google', 'microsoft'):
            return Response(
                {'error': 'Параметр provider должен быть "google" или "microsoft".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate cryptographically random state for CSRF protection
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        request.session['oauth_provider'] = provider
        request.session.modified = True

        if provider == 'google':
            auth_url = get_google_auth_url(state)
        else:
            auth_url = get_microsoft_auth_url(state)

        return Response({
            'auth_url': auth_url,
            'provider': provider,
        })


class OAuthCallbackView(APIView):
    """
    GET /api/email/oauth/callback/?code=...&state=...
    Validates CSRF state, exchanges the authorization code for tokens,
    encrypts them via AES-256-GCM, and stores in the database.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')

        # Provider denied access
        if error:
            return Response(
                {'error': f'Провайдер отклонил запрос: {error}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code or not state:
            return Response(
                {'error': 'Отсутствуют параметры code или state.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---- CSRF state validation ----
        saved_state = request.session.pop('oauth_state', None)
        provider = request.session.pop('oauth_provider', None)

        if not saved_state or state != saved_state:
            return Response(
                {'error': 'Неверный параметр state. Возможна CSRF-атака.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            if provider == 'google':
                token_data = exchange_google_code(code)
                user_email = get_google_user_email(token_data['access_token'])
                scope = GOOGLE_SCOPES
            elif provider == 'microsoft':
                token_data = exchange_microsoft_code(code)
                user_email = get_microsoft_user_email(token_data['access_token'])
                scope = MICROSOFT_SCOPES
            else:
                return Response(
                    {'error': f'Неизвестный провайдер: {provider}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as exc:
            return Response(
                {'error': f'Ошибка обмена кода на токен: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ---- Store encrypted tokens ----
        expires_at = timezone.now() + td(seconds=token_data.get('expires_in', 3600))

        token_obj, _created = EmailOAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                'provider': provider,
                'token_expires_at': expires_at,
                'scope': scope,
                'user_email': user_email,
            },
        )
        # Use property setters which encrypt automatically
        token_obj.access_token = token_data['access_token']
        token_obj.refresh_token = token_data.get('refresh_token', '')
        token_obj.save()

        return Response({
            'status': 'connected',
            'provider': provider,
            'email': user_email,
        })


class OAuthStatusView(APIView):
    """
    GET /api/email/oauth/status/
    Returns the current OAuth connection status for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            token_obj = EmailOAuthToken.objects.get(user=request.user)
            return Response({
                'connected': True,
                'provider': token_obj.provider,
                'email': token_obj.user_email,
                'primary_email': request.user.email,
                'connected_at': token_obj.created_at,
                'token_expires_at': token_obj.token_expires_at,
            })
        except EmailOAuthToken.DoesNotExist:
            return Response({
                'connected': False,
                'provider': None,
                'email': None,
                'primary_email': request.user.email,
            })


class OAuthDisconnectView(APIView):
    """
    DELETE /api/email/oauth/disconnect/
    Removes the OAuth token, disconnecting the user's email provider.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted, _ = EmailOAuthToken.objects.filter(user=request.user).delete()
        if deleted:
            return Response({'status': 'disconnected'})
        return Response(
            {'error': 'Нет подключённой почты для отключения.'},
            status=status.HTTP_404_NOT_FOUND,
        )
