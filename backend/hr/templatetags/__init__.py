from django import template
from hr.roles import has_hr_group

register = template.Library()


@register.simple_tag(takes_context=True)
def has_hr_access(context):
    """
    Template tag to check if current user has HR access.

    Usage in templates:
        {% load hr_tags %}
        {% has_hr_access as can_see_hr %}
        {% if can_see_hr %}
            ... HR links ...
        {% endif %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False
    user = request.user
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return has_hr_group(user)
