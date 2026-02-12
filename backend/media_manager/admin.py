from django.contrib import admin

from .models import News, ContactRequest


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'published', 'published_at')
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'handled', 'replied_at', 'created_at')
    list_filter = ('handled', 'replied_at', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'message', 'reply_message')
