from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
        ('tasks', '0004_task_ordering_priority_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='team',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tasks',
                to='teams.team',
                verbose_name='Equipe',
            ),
        ),
    ]
