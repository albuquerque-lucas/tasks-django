from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed initial users and assign groups'

    def handle(self, *args, **options):
        users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'password': 'admin123',
                'role': 'super_admin',
                'is_superuser': True,
            },
            {
                'username': 'lucaslpra',
                'email': 'lucaslpra@example.com',
                'first_name': 'Lucas',
                'last_name': 'Albuquerque',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
        ]

        groups = {
            'super_admin': Group.objects.get_or_create(name='super_admin')[0],
            'company_admin': Group.objects.get_or_create(name='company_admin')[0],
            'standard_user': Group.objects.get_or_create(name='standard_user')[0],
        }

        for user_data in users:
            password = user_data.pop('password')
            role = user_data.pop('role')
            is_superuser = user_data.pop('is_superuser')

            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )

            if created:
                user.set_password(password)

            user.is_superuser = is_superuser
            user.save()
            user.groups.add(groups[role])

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'User "{user_data["username"]}" created.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'User "{user_data["username"]}" already exists.'
                    )
                )
