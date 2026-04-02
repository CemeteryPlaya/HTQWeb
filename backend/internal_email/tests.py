"""
Unit tests for the OAuth 2.0 email integration module.

Covers:
- AES-256-GCM crypto roundtrip and tamper detection
- CRLF injection sanitization in MIME headers
- OAuth state CSRF validation
"""
import base64
import os
from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone

User = get_user_model()

# A deterministic test encryption key (32 bytes, base64-encoded)
TEST_ENCRYPTION_KEY = base64.b64encode(os.urandom(32)).decode()


# ═══════════════════════════════════════════════════════════════════════════
#  1. Crypto Tests
# ═══════════════════════════════════════════════════════════════════════════

@override_settings(OAUTH_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class CryptoTests(TestCase):
    """Tests for internal_email.crypto (AES-256-GCM)."""

    def setUp(self):
        # Reset cached key between tests
        from internal_email import crypto
        crypto._cached_key = None

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt → Decrypt produces the original plaintext."""
        from internal_email.crypto import encrypt, decrypt

        plaintext = 'ya29.a0ARrdaM8_super_secret_access_token_value'
        blob = encrypt(plaintext)
        result = decrypt(blob)
        self.assertEqual(result, plaintext)

    def test_encrypt_produces_unique_nonce(self):
        """Each encryption call must produce a different nonce (first 12 bytes)."""
        from internal_email.crypto import encrypt

        blob1 = encrypt('same-plaintext')
        blob2 = encrypt('same-plaintext')

        nonce1 = blob1[:12]
        nonce2 = blob2[:12]
        self.assertNotEqual(nonce1, nonce2, 'Nonce reuse detected!')

    def test_tampered_ciphertext_raises(self):
        """Modifying the ciphertext must raise InvalidTag."""
        from internal_email.crypto import encrypt, decrypt
        from cryptography.exceptions import InvalidTag

        blob = encrypt('sensitive-data')
        # Flip a byte in the ciphertext (after the 12-byte nonce)
        tampered = blob[:15] + bytes([blob[15] ^ 0xFF]) + blob[16:]

        with self.assertRaises(InvalidTag):
            decrypt(tampered)

    def test_empty_plaintext_raises(self):
        """Encrypting empty string must raise ValueError."""
        from internal_email.crypto import encrypt

        with self.assertRaises(ValueError):
            encrypt('')

    def test_short_blob_raises(self):
        """Decrypting a too-short blob must raise ValueError."""
        from internal_email.crypto import decrypt

        with self.assertRaises(ValueError):
            decrypt(b'short')


# ═══════════════════════════════════════════════════════════════════════════
#  2. MIME Sanitization Tests
# ═══════════════════════════════════════════════════════════════════════════

class MIMESanitizationTests(TestCase):
    """Tests for CRLF injection protection in mta_connector."""

    def test_crlf_stripped_from_subject(self):
        from internal_email.mta_connector import _sanitize_header
        malicious = 'Normal Subject\r\nBcc: evil@hacker.com'
        result = _sanitize_header(malicious)
        self.assertNotIn('\r', result)
        self.assertNotIn('\n', result)
        self.assertIn('Normal Subject', result)

    def test_crlf_stripped_from_sender_name(self):
        from internal_email.mta_connector import _sanitize_header
        malicious = 'John Doe\r\nBcc: evil@hacker.com'
        result = _sanitize_header(malicious)
        self.assertNotIn('\r', result)
        self.assertNotIn('\n', result)

    def test_clean_subject_passes_through(self):
        from internal_email.mta_connector import _sanitize_header
        clean = 'Quarterly Report Q1 2026'
        result = _sanitize_header(clean)
        self.assertEqual(result, clean)

    def test_email_address_sanitized(self):
        from internal_email.mta_connector import _sanitize_email_address
        malicious = 'user@example.com\r\nBcc: evil@hacker.com'
        result = _sanitize_email_address(malicious)
        self.assertNotIn('\r', result)
        self.assertNotIn('\n', result)

    def test_mime_message_headers_safe(self):
        from internal_email.mta_connector import _build_mime_message
        msg = _build_mime_message(
            sender_email='user@company.com',
            sender_name='John\r\nBcc: evil@hacker.com',
            recipients=['client@example.com\r\nBcc: evil@hacker.com'],
            subject='Hello\r\nBcc: evil@hacker.com',
            body_html='<p>Test</p>',
        )
        raw = msg.as_string()
        # The important thing: no line starts with 'Bcc:' as a real header.
        # After CRLF stripping, the text "Bcc: ..." becomes part of
        # the value (harmless), not a separate header line.
        for line in raw.split('\n'):
            self.assertFalse(
                line.strip().startswith('Bcc:'),
                f'Injected Bcc header found: {line}'
            )


# ═══════════════════════════════════════════════════════════════════════════
#  3. OAuth State CSRF Tests
# ═══════════════════════════════════════════════════════════════════════════

class OAuthStateTests(TestCase):
    """Tests for OAuth CSRF state validation in views."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testemployee',
            password='testpass123',
            email='test@company.com',
        )

    def _make_request_with_session(self, query_params, session_data=None):
        """Helper: create a GET request with a real session."""
        from internal_email.views import OAuthCallbackView

        url = '/api/email/oauth/callback/?' + '&'.join(
            f'{k}={v}' for k, v in query_params.items()
        )
        request = self.factory.get(url)
        request.user = self.user

        # Attach a real session
        session = SessionStore()
        if session_data:
            for k, v in session_data.items():
                session[k] = v
            session.save()
        request.session = session

        # Manually set query_params
        request.query_params = query_params

        view = OAuthCallbackView()
        return view.get(request)

    def test_mismatched_state_returns_403(self):
        """Callback must reject when state param doesn't match session."""
        response = self._make_request_with_session(
            query_params={'code': 'test-code', 'state': 'wrong-state'},
            session_data={'oauth_state': 'correct-state', 'oauth_provider': 'google'},
        )
        self.assertEqual(response.status_code, 403)

    def test_missing_state_returns_400(self):
        """Callback must reject when state param is missing."""
        response = self._make_request_with_session(
            query_params={'code': 'test-code'},
            session_data={'oauth_state': 'some-state', 'oauth_provider': 'google'},
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_code_returns_400(self):
        """Callback must reject when code param is missing."""
        response = self._make_request_with_session(
            query_params={'state': 'some-state'},
            session_data={'oauth_state': 'some-state', 'oauth_provider': 'google'},
        )
        self.assertEqual(response.status_code, 400)

    def test_no_session_state_returns_403(self):
        """Callback must reject when no state was ever saved in session."""
        response = self._make_request_with_session(
            query_params={'code': 'test-code', 'state': 'any-state'},
            session_data={},  # empty session
        )
        self.assertEqual(response.status_code, 403)

    def test_provider_error_returns_400(self):
        """Callback must handle provider error gracefully."""
        response = self._make_request_with_session(
            query_params={'error': 'access_denied'},
            session_data={'oauth_state': 'some-state', 'oauth_provider': 'google'},
        )
        self.assertEqual(response.status_code, 400)


class OAuthStatusTests(TestCase):
    """Tests for OAuth status endpoint and primary_email field."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='statustest',
            password='testpass123',
            email='status@company.com',
        )

    def test_unconnected_returns_primary_email(self):
        """OAuthStatusView must return primary_email even if not connected."""
        from internal_email.views import OAuthStatusView
        request = self.factory.get('/api/email/oauth/status/')
        request.user = self.user
        
        view = OAuthStatusView()
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['connected'])
        self.assertEqual(response.data['primary_email'], 'status@company.com')

    def test_connected_returns_both_emails(self):
        """OAuthStatusView must return both primary and oauth emails when connected."""
        from internal_email.views import OAuthStatusView
        from internal_email.models import EmailOAuthToken
        
        EmailOAuthToken.objects.create(
            user=self.user,
            provider='google',
            user_email='google@gmail.com',
            token_expires_at=timezone.now() + timedelta(hours=1)
        )
        
        request = self.factory.get('/api/email/oauth/status/')
        request.user = self.user
        
        view = OAuthStatusView()
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['connected'])
        self.assertEqual(response.data['email'], 'google@gmail.com')
        self.assertEqual(response.data['primary_email'], 'status@company.com')
