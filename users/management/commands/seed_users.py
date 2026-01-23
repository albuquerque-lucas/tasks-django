from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Popula usuários iniciais para desenvolvimento'

    def handle(self, *args, **options):
        users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'password': 'admin123',
            },
            {
                'username': 'lucaslpra',
                'email': 'lucaslpra@example.com',
                'first_name': 'Lucas',
                'last_name': 'Albuquerque',
                'password': '123123123',
            },
        ]

        for user_data in users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Usuário "{user_data["username"]}" criado com sucesso!'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Usuário "{user_data["username"]}" já existe!'
                    )
                )
