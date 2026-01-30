from django.core.management.base import BaseCommand, CommandError

from safetodo.services.meili import (
    build_auditlog_document,
    ensure_auditlogs_index,
    get_auditlogs_index,
)
from auditlogs.models import AuditLog


class Command(BaseCommand):
    help = 'Reindexa audit logs no Meilisearch'

    def handle(self, *args, **options):
        index = get_auditlogs_index()
        if index is None:
            raise CommandError('Meilisearch nao configurado (MEILI_HOST).')

        ensure_auditlogs_index(index)
        index.delete_all_documents()

        total = 0
        batch = []
        batch_size = 500

        queryset = AuditLog.objects.select_related('user')
        for log in queryset.iterator():
            batch.append(build_auditlog_document(log))
            if len(batch) >= batch_size:
                index.add_documents(batch, primary_key='id')
                total += len(batch)
                self.stdout.write(f'Indexados: {total}')
                batch = []

        if batch:
            index.add_documents(batch, primary_key='id')
            total += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Reindex concluido: {total} logs.'))
