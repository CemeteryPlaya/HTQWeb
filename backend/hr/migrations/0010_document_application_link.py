from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0009_create_rbac_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='application',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='documents',
                to='hr.application',
                verbose_name='Заявка',
            ),
        ),
    ]
