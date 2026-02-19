from django.db import migrations


class Migration(migrations.Migration):
    """
    State-only migration: remove task models from the 'hr' app state.
    The actual tables remain in the database and are now owned by the 'tasks' app.
    """

    dependencies = [
        ('hr', '0012_tasks_roadmap_labels'),
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='TaskAttachment'),
                migrations.DeleteModel(name='TaskComment'),
                migrations.RemoveField(model_name='task', name='labels'),
                migrations.DeleteModel(name='Task'),
                migrations.DeleteModel(name='ProjectVersion'),
                migrations.DeleteModel(name='Label'),
            ],
            database_operations=[],
        ),
    ]
