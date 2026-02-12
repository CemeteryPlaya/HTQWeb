from django.conf import settings
from django.db import models


class News(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True, allow_unicode=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'mainView_news'

    def __str__(self):
        return self.title


class ContactRequest(models.Model):
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    message = models.TextField(blank=True)
    handled = models.BooleanField(default=False, db_index=True)
    replied_at = models.DateTimeField(null=True, blank=True, db_index=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_replies',
    )
    reply_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mainView_contactrequest'

    def __str__(self):
        return f"{self.email} — {self.first_name} {self.last_name}"
