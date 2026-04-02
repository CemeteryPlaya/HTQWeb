from django.urls import path
from .views import (
    InboxView,
    SentView,
    DraftsView,
    TrashView,
    EmailSendView,
    EmailDraftView,
    EmailReadView,
    OAuthInitView,
    OAuthCallbackView,
    OAuthStatusView,
    OAuthDisconnectView,
)

app_name = 'internal_email'

urlpatterns = [
    path('inbox/', InboxView.as_view(), name='inbox'),
    path('sent/', SentView.as_view(), name='sent'),
    path('drafts/', DraftsView.as_view(), name='drafts'),
    path('trash/', TrashView.as_view(), name='trash'),
    path('send/', EmailSendView.as_view(), name='send'),
    path('draft/', EmailDraftView.as_view(), name='draft'),
    path('<int:pk>/read/', EmailReadView.as_view(), name='read'),
    # OAuth 2.0
    path('oauth/init/', OAuthInitView.as_view(), name='oauth_init'),
    path('oauth/callback/', OAuthCallbackView.as_view(), name='oauth_callback'),
    path('oauth/status/', OAuthStatusView.as_view(), name='oauth_status'),
    path('oauth/disconnect/', OAuthDisconnectView.as_view(), name='oauth_disconnect'),
]
