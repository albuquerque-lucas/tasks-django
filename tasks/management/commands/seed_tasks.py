from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tasks.models import PriorityLevel, Task


class Command(BaseCommand):
    help = 'Popula tarefa inicial para desenvolvimento'

    def handle(self, *args, **options):
        UserModel = get_user_model()
        admin_user = UserModel.objects.filter(id=1).first()
        if not admin_user:
            self.stdout.write(
                self.style.WARNING('Usuario com ID 1 nao encontrado.')
            )
            return

        default_priority = PriorityLevel.objects.filter(level=1).first()
        if not default_priority:
            default_priority = PriorityLevel.objects.order_by('level').first()

        task, created = Task.objects.get_or_create(
            title='Tarefa inicial',
            user=admin_user,
            defaults={
                'description': 'Tarefa seeded para o usuario admin.',
                'status': 'created',
                'priority_level': default_priority,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('Tarefa inicial criada com sucesso.')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Tarefa inicial ja existe.')
            )

