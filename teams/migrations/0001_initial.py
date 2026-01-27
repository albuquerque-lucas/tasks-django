from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0002_user_date_joined_user_groups_user_is_staff'),
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=150, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('members', models.ManyToManyField(blank=True, related_name='teams', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Equipe',
                'verbose_name_plural': 'Equipes',
            },
        ),
    ]
