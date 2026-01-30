from django.core.management.base import BaseCommand, CommandError

from safetodo.services.meili import (
    build_task_document,
    ensure_tasks_index,
    get_tasks_index,
)
from tasks.models import Task


class Command(BaseCommand):
    help = 'Reindexa tarefas no Meilisearch'

    def handle(self, *args, **options):
        index = get_tasks_index()
        if index is None:
            raise CommandError('Meilisearch nao configurado (MEILI_HOST).')

        ensure_tasks_index(index)
        index.delete_all_documents()

        total = 0
        batch = []
        batch_size = 500

        queryset = Task.objects.select_related('user', 'team', 'priority_level')
        for task in queryset.iterator():
            batch.append(build_task_document(task))
            if len(batch) >= batch_size:
                index.add_documents(batch, primary_key='id')
                total += len(batch)
                self.stdout.write(f'Indexados: {total}')
                batch = []

        if batch:
            index.add_documents(batch, primary_key='id')
            total += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Reindex concluido: {total} tarefas.'))
