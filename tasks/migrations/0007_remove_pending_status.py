from django.db import migrations, models


def migrate_pending_to_in_progress(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    Task.objects.filter(status='pending').update(status='in_progress')


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_task_status_created'),
    ]

    operations = [
        migrations.RunPython(migrate_pending_to_in_progress, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(
                choices=[
                    ('created', 'Criada'),
                    ('in_progress', 'Em Progresso'),
                    ('completed', 'ConcluÃ­da'),
                    ('cancelled', 'Cancelada'),
                ],
                default='created',
                max_length=20,
                verbose_name='Status',
            ),
        ),
    ]
