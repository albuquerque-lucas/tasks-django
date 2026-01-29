from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0005_task_team'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(
                choices=[
                    ('created', 'Criada'),
                    ('pending', 'Pendente'),
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
