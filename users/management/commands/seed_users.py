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
                'email': 'admin@system.com',
                'first_name': 'Admin',
                'last_name': 'System',
                'password': 'admin123',
                'role': 'super_admin',
                'is_superuser': True,
            },
            {
                'username': 'lucas.albuquerque',
                'email': 'lucas.albuquerque@admin.com',
                'first_name': 'Lucas',
                'last_name': 'Albuquerque',
                'password': '123123123',
                'role': 'super_admin',
                'is_superuser': True,
            },
            {
                'username': 'matheus.soldati',
                'email': 'matheus.soldati@admin.com',
                'first_name': 'Matheus',
                'last_name': 'Soldati',
                'password': '123123123',
                'role': 'super_admin',
                'is_superuser': True,
            },
            {
                'username': 'renata.silva',
                'email': 'renata.silva@company_admin.com',
                'first_name': 'Renata',
                'last_name': 'Silva',
                'password': '123123123',
                'role': 'company_admin',
                'is_superuser': False,
            },
            {
                'username': 'paulo.souza',
                'email': 'paulo.souza@company_admin.com',
                'first_name': 'Paulo',
                'last_name': 'Souza',
                'password': '123123123',
                'role': 'company_admin',
                'is_superuser': False,
            },
            {
                'username': 'ana.carvalho',
                'email': 'ana.carvalho@user.com',
                'first_name': 'Ana',
                'last_name': 'Carvalho',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'bruno.mendes',
                'email': 'bruno.mendes@user.com',
                'first_name': 'Bruno',
                'last_name': 'Mendes',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'carla.oliveira',
                'email': 'carla.oliveira@user.com',
                'first_name': 'Carla',
                'last_name': 'Oliveira',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'diego.santos',
                'email': 'diego.santos@user.com',
                'first_name': 'Diego',
                'last_name': 'Santos',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'elisa.pereira',
                'email': 'elisa.pereira@user.com',
                'first_name': 'Elisa',
                'last_name': 'Pereira',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'fabio.ramos',
                'email': 'fabio.ramos@user.com',
                'first_name': 'Fabio',
                'last_name': 'Ramos',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'gabriela.lima',
                'email': 'gabriela.lima@user.com',
                'first_name': 'Gabriela',
                'last_name': 'Lima',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'henrique.alves',
                'email': 'henrique.alves@user.com',
                'first_name': 'Henrique',
                'last_name': 'Alves',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'isabela.fernandes',
                'email': 'isabela.fernandes@user.com',
                'first_name': 'Isabela',
                'last_name': 'Fernandes',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'joao.costa',
                'email': 'joao.costa@user.com',
                'first_name': 'Joao',
                'last_name': 'Costa',
                'password': '123123123',
                'role': 'standard_user',
                'is_superuser': False,
            },
            {
                'username': 'lara.barros',
                'email': 'lara.barros@user.com',
                'first_name': 'Lara',
                'last_name': 'Barros',
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
