from django.contrib import admin
from .models import EmailMessage, EmailRecipientStatus, EmailAttachment

@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'sender', 'is_draft', 'created_at', 'sent_at')
    list_filter = ('is_draft', 'created_at')
    search_fields = ('subject', 'sender__username', 'sender__email')

@admin.register(EmailRecipientStatus)
class EmailRecipientStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'recipient_type', 'folder', 'is_read')
    list_filter = ('folder', 'recipient_type', 'is_read')
    search_fields = ('user__username', 'user__email', 'message__subject')

@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file', 'uploaded_at')
