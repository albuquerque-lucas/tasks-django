from django.core.management.base import BaseCommand
from tasks.models import PriorityLevel


class Command(BaseCommand):
    help = 'Popula niveis de prioridade iniciais'

    def handle(self, *args, **options):
        levels = [
            (1, 'Urgente', 'Mais importante'),
            (2, 'Alta', 'Alta prioridade'),
            (3, 'Media', 'Prioridade media'),
            (4, 'Baixa', 'Prioridade baixa'),
            (5, 'Minima', 'Menos importante'),
        ]

        for level, name, description in levels:
            priority_level, created = PriorityLevel.objects.update_or_create(
                level=level,
                defaults={
                    'name': name,
                    'description': description,
                    'is_active': True,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Nivel {priority_level.level} criado com sucesso.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Nivel {priority_level.level} ja existe.'
                    )
                )
