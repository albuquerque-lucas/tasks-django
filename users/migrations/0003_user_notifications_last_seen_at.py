from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_user_date_joined_user_groups_user_is_staff'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='notifications_last_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
