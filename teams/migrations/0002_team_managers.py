from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='managers',
            field=models.ManyToManyField(
                blank=True,
                related_name='managed_teams',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
