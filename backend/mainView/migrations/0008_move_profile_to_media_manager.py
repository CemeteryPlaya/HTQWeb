"""Remove Profile model from mainView state (table stays as-is, now managed by media_manager)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mainView', '0007_alter_news_slug_allow_unicode'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='Profile'),
            ],
            database_operations=[],  # Don't touch the DB – media_manager takes ownership
        ),
    ]
