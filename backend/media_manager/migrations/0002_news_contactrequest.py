"""Add News and ContactRequest models to media_manager state, pointing at existing tables."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('media_manager', '0001_initial'),
        ('mainView', '0009_move_news_contacts_to_media_manager'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='News',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=300)),
                        ('slug', models.SlugField(allow_unicode=True, max_length=320, unique=True)),
                        ('summary', models.TextField(blank=True)),
                        ('content', models.TextField(blank=True)),
                        ('image', models.ImageField(blank=True, null=True, upload_to='news_images/')),
                        ('category', models.CharField(blank=True, db_index=True, max_length=100)),
                        ('published', models.BooleanField(db_index=True, default=False)),
                        ('published_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                    ],
                    options={
                        'db_table': 'mainView_news',
                    },
                ),
                migrations.CreateModel(
                    name='ContactRequest',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('first_name', models.CharField(blank=True, max_length=150)),
                        ('last_name', models.CharField(blank=True, max_length=150)),
                        ('email', models.EmailField(max_length=254)),
                        ('message', models.TextField(blank=True)),
                        ('handled', models.BooleanField(db_index=True, default=False)),
                        ('replied_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                        ('replied_by', models.ForeignKey(
                            blank=True,
                            null=True,
                            on_delete=django.db.models.deletion.SET_NULL,
                            related_name='contact_replies',
                            to=settings.AUTH_USER_MODEL,
                        )),
                        ('reply_message', models.TextField(blank=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                    ],
                    options={
                        'db_table': 'mainView_contactrequest',
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
