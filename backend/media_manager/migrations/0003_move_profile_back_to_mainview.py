"""Remove Profile from media_manager state (table stays, ownership returns to mainView)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('media_manager', '0002_news_contactrequest'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='Profile'),
            ],
            database_operations=[],
        ),
    ]
