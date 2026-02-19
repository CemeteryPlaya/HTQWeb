"""
Global audit middleware — logs all mutating API requests (POST, PUT, PATCH, DELETE)
and login/register events to HRActionLog.
HR endpoints are skipped (they have their own detailed logging via log_action).
"""
import json

from django.contrib.auth.models import AnonymousUser

from hr.models import HRActionLog


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# Map URL patterns to (module, target_type) tuples
URL_RULES = [
    # Auth
    ('/api/token/', HRActionLog.Module.AUTH, HRActionLog.TargetType.AUTH),
    ('/api/v1/register/', HRActionLog.Module.AUTH, HRActionLog.TargetType.USER),
    # News
    ('/api/news/', HRActionLog.Module.NEWS, HRActionLog.TargetType.NEWS),
    # Profile
    ('/api/v1/profile/', HRActionLog.Module.PROFILE, HRActionLog.TargetType.PROFILE),
    # Contacts
    ('/api/v1/contact-requests/', HRActionLog.Module.CONTACTS, HRActionLog.TargetType.CONTACT_REQUEST),
    # Admin users
    ('/api/v1/admin/users/', HRActionLog.Module.ADMIN, HRActionLog.TargetType.USER),
    # Items
    ('/api/items/', HRActionLog.Module.OTHER, HRActionLog.TargetType.OTHER),
]

# Methods that indicate write actions
WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

# Skip these paths entirely
SKIP_PATHS = ['/admin/', '/api/v1/contact-requests/stats/', '/api/hr/']

# Method to action type map
METHOD_ACTION_MAP = {
    'POST': HRActionLog.ActionType.CREATE,
    'PUT': HRActionLog.ActionType.UPDATE,
    'PATCH': HRActionLog.ActionType.UPDATE,
    'DELETE': HRActionLog.ActionType.DELETE,
}


def _extract_id_from_path(path):
    """Extract numeric ID from URL path like /api/news/5/ → 5."""
    parts = path.rstrip('/').split('/')
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return None


def _classify_request(path, method):
    """Determine module and target type from URL path."""
    for pattern, module, target_type in URL_RULES:
        if pattern in path:
            # Special: token endpoint = login
            if '/api/token/' in path and method == 'POST':
                if 'refresh' in path:
                    return None  # skip token refresh — too noisy
                return module, target_type, HRActionLog.ActionType.LOGIN
            # Register = create user
            if '/api/v1/register/' in path and method == 'POST':
                return module, target_type, HRActionLog.ActionType.CREATE
            action = METHOD_ACTION_MAP.get(method, HRActionLog.ActionType.OTHER)
            return module, target_type, action
    return None


def _build_details(request, response, path, method, action):
    """Build target_repr, target_id and details from request/response data."""
    target_repr = ''
    target_id = _extract_id_from_path(path)
    details = f'{method} {path}'

    # Try to extract useful info from response
    data = getattr(response, 'data', None)
    if isinstance(data, dict):
        # Get id
        if 'id' in data:
            target_id = data['id']
        # Get a meaningful representation
        for key in ['title', 'name', 'display_name', 'full_name', 'slug',
                     'first_name', 'username', 'email']:
            if key in data and data[key]:
                target_repr = str(data[key])[:200]
                break
        # Compose details
        if target_id:
            details = f'{method} {path} (id={target_id})'
    elif method == 'DELETE' and target_id:
        target_repr = f'id={target_id}'

    # For login, try to get the email/username from request body
    if action == HRActionLog.ActionType.LOGIN:
        try:
            body = json.loads(request.body)
            target_repr = body.get('email', body.get('username', ''))
            details = f'Login: {target_repr}'
        except Exception:
            pass

    # For register, get username from response
    if '/register/' in path and isinstance(data, dict):
        username = data.get('username', '')
        email = data.get('email', '')
        target_repr = username or email
        details = f'Register: {target_repr}'

    # For contact requests (public), get sender info
    if '/contact-requests/' in path and method == 'POST' and isinstance(data, dict):
        name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        email = data.get('email', '')
        target_repr = f'{name} ({email})' if name else email
        details = f'Contact request from {target_repr}'

    # For news, get title
    if '/news/' in path and isinstance(data, dict):
        title = data.get('title', '')
        if title:
            target_repr = title
            if method == 'POST':
                details = f'News created: {title}'
            elif method in ('PUT', 'PATCH'):
                details = f'News updated: {title}'
            elif method == 'DELETE':
                details = f'News deleted: id={target_id}'

    # For profile, get display_name
    if '/profile/' in path and isinstance(data, dict):
        display = data.get('display_name', '') or data.get('email', '')
        if display:
            target_repr = display
            details = f'Profile updated: {display}'

    # For admin users
    if '/admin/users/' in path and isinstance(data, dict):
        username = data.get('username', '')
        if username:
            target_repr = username
            details = f'User updated: {username}'

    return target_repr, target_id, details


class AuditLogMiddleware:
    """
    Middleware that logs all mutating API requests to HRActionLog.
    HR endpoints are skipped (they have their own detailed logging).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only log API requests
        path = request.path
        if not path.startswith('/api/'):
            return response

        method = request.method

        # Skip safe methods (GET, HEAD, OPTIONS)
        if method not in WRITE_METHODS:
            return response

        # Skip excluded endpoints (HR has its own logging, admin panel, stats)
        for skip in SKIP_PATHS:
            if skip in path:
                return response

        # Only log successful responses (2xx)
        if response.status_code < 200 or response.status_code >= 300:
            return response

        classification = _classify_request(path, method)
        if not classification:
            return response

        module, target_type, action = classification

        user = getattr(request, 'user', None)
        if user is None or isinstance(user, AnonymousUser):
            # For login/register/contact-requests, user is anonymous
            if action in (HRActionLog.ActionType.LOGIN, HRActionLog.ActionType.CREATE):
                user = None
            elif '/contact-requests/' in path:
                user = None
            else:
                return response

        target_repr, target_id, details = _build_details(
            request, response, path, method, action
        )

        try:
            HRActionLog.objects.create(
                user=user if user and not isinstance(user, AnonymousUser) else None,
                action=action,
                target_type=target_type,
                target_id=target_id,
                target_repr=str(target_repr)[:500],
                details=str(details)[:2000],
                ip_address=_get_client_ip(request),
                url=path[:500],
                module=module,
            )
        except Exception:
            pass

        return response
