"""Restore Profile model in mainView state (table mainView_profile already exists)."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainView', '0009_move_news_contacts_to_media_manager'),
        ('media_manager', '0003_move_profile_back_to_mainview'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Profile',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('display_name', models.CharField(blank=True, max_length=100)),
                        ('bio', models.TextField(blank=True, max_length=1000)),
                        ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
                        ('settings', models.JSONField(blank=True, default=dict)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('user', models.OneToOneField(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='profile',
                            to=settings.AUTH_USER_MODEL,
                        )),
                    ],
                ),
            ],
            database_operations=[],
        ),
    ]
