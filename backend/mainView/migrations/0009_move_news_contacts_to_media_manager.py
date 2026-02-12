"""Remove News and ContactRequest from mainView state (tables stay, now managed by media_manager)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mainView', '0008_move_profile_to_media_manager'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='News'),
                migrations.DeleteModel(name='ContactRequest'),
            ],
            database_operations=[],
        ),
    ]
