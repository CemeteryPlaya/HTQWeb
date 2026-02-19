# ---------------------------------------------------------------
#  HR Role definitions (RBAC)
# ---------------------------------------------------------------
import logging

logger = logging.getLogger('hr.roles')

# Canonical group names stored in auth_group
SENIOR_HR_GROUP = 'senior_hr'
JUNIOR_HR_GROUP = 'junior_hr'

# Legacy group names kept for backward-compatibility; users in these
# groups are treated as senior_hr.  ALL LOWERCASE — comparison is
# always done against lowered actual group names.
LEGACY_SENIOR_GROUPS = (
    'hr_manager',
    'hr manager',
    'senior manager',
    'staff',
    'staf',
)

# Legacy group names treated as junior_hr
LEGACY_JUNIOR_GROUPS = ('junior manager',)

# All groups that grant *any* HR access
HR_GROUP_NAMES = (
    SENIOR_HR_GROUP,
    JUNIOR_HR_GROUP,
    *LEGACY_SENIOR_GROUPS,
    *LEGACY_JUNIOR_GROUPS,
)

# Groups whose members are treated as Senior HR (full access)
SENIOR_GROUPS = (SENIOR_HR_GROUP, *LEGACY_SENIOR_GROUPS)


def _user_group_names(user) -> set[str]:
    """Return normalized (lowered, stripped) group names.

    Cached on the user instance for the duration of the request.
    Any DB error is caught so that we never accidentally cause a 403
    just because a group query failed.
    """
    if not user or not user.is_authenticated:
        return set()
    if not hasattr(user, '_cached_group_names'):
        try:
            user._cached_group_names = set(
                name.strip().lower()
                for name in user.groups.values_list('name', flat=True)
            )
        except Exception:
            logger.exception(
                'Failed to load groups for user %s (pk=%s). '
                'Falling back to empty set.',
                getattr(user, 'username', '?'),
                getattr(user, 'pk', '?'),
            )
            user._cached_group_names = set()
    return user._cached_group_names


def _is_privileged(user) -> bool:
    """Return True if the user is a superuser or staff.

    This is the PRIMARY bypass — if True the user gets senior-level
    access regardless of groups.  We check both flags with getattr
    so a broken user object never causes a crash.
    """
    return bool(
        getattr(user, 'is_superuser', False)
        or getattr(user, 'is_staff', False)
    )


def has_hr_group(user) -> bool:
    """Return True if user is in *any* HR group (or is privileged)."""
    if _is_privileged(user):
        return True
    return bool(_user_group_names(user) & set(HR_GROUP_NAMES))


def is_senior_hr(user) -> bool:
    """
    Full-access HR role:
    • superuser / staff → always True
    • member of senior_hr / any legacy senior-level group → True
    """
    if not user or not user.is_authenticated:
        return False
    if _is_privileged(user):
        return True
    return bool(_user_group_names(user) & set(SENIOR_GROUPS))


def is_junior_hr(user) -> bool:
    """
    Limited-access HR role: member of junior_hr group
    (but NOT senior / superuser / staff — those are already senior).
    """
    if not user or not user.is_authenticated:
        return False
    names = _user_group_names(user)
    return bool(names & {JUNIOR_HR_GROUP, *LEGACY_JUNIOR_GROUPS})


def get_hr_level(user) -> str | None:
    """
    Return 'senior', 'junior' or None.
    superuser / staff / senior groups → 'senior'.
    junior_hr group only              → 'junior'.
    no HR group                       → None.
    """
    if is_senior_hr(user):
        return 'senior'
    if is_junior_hr(user):
        return 'junior'
    return None
