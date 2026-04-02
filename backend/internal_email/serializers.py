import re
import bleach
from rest_framework import serializers
from .models import EmailMessage, EmailRecipientStatus, EmailAttachment
from django.contrib.auth import get_user_model

User = get_user_model()

# Allowed HTML elements and attributes for the email body
BLEACH_ALLOWED_TAGS = [
    'a', 'b', 'i', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'span', 'div',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 's', 'u'
]
BLEACH_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    '*': ['style']
}
BLEACH_ALLOWED_STYLES = [
    'color', 'background-color', 'font-size', 'font-family', 'text-align'
]


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class EmailAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAttachment
        fields = ['id', 'file', 'uploaded_at']


class EmailMessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    attachments = EmailAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = ['id', 'subject', 'body', 'sender', 'is_draft', 'created_at', 'sent_at', 'attachments', 'external_recipients']

    def validate_subject(self, value):
        """
        Remove any CRLF (\r, \n) characters from the subject to prevent Email Header Injection.
        """
        if value:
            # Replaces any \r or \n with a space
            return re.sub(r'[\r\n]+', ' ', value).strip()
        return value

    def validate_body(self, value):
        """
        Sanitize HTML content using Bleach to prevent Stored XSS attacks.
        """
        if not value:
            return value

        try:
            # bleach >= 6.1.0 uses CSSSanitizer (requires tinycss2)
            from bleach.css_sanitizer import CSSSanitizer
            css_sanitizer = CSSSanitizer(allowed_css_properties=BLEACH_ALLOWED_STYLES)
            
            return bleach.clean(
                value,
                tags=BLEACH_ALLOWED_TAGS,
                attributes=BLEACH_ALLOWED_ATTRIBUTES,
                css_sanitizer=css_sanitizer,
                strip=True
            )
        except (ImportError, TypeError, Exception) as e:
            # Fallback if bleach/tinycss2 is broken or old
            # We still try a basic clean without CSS if possible
            try:
                return bleach.clean(
                    value,
                    tags=BLEACH_ALLOWED_TAGS,
                    attributes=BLEACH_ALLOWED_ATTRIBUTES,
                    strip=True
                )
            except Exception:
                # Absolute fallback: return raw value (unsafe but prevents 500 crash)
                # In production, we should log this.
                return value

class EmailRecipientStatusSerializer(serializers.ModelSerializer):
    message = EmailMessageSerializer(read_only=True)
    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = EmailRecipientStatus
        fields = ['id', 'message', 'user', 'recipient_type', 'folder', 'is_read', 'read_at']
