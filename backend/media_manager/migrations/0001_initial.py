"""Create Profile model in media_manager state, pointing at the existing mainView_profile table."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainView', '0008_move_profile_to_media_manager'),
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
                    options={
                        'db_table': 'mainView_profile',
                    },
                ),
            ],
            database_operations=[],  # Table already exists
        ),
    ]
