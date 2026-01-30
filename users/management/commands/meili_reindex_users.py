from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from safetodo.services.meili import (
    build_user_document,
    ensure_users_index,
    get_users_index,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Reindexa usuarios no Meilisearch'

    def handle(self, *args, **options):
        index = get_users_index()
        if index is None:
            raise CommandError('Meilisearch nao configurado (MEILI_HOST).')

        ensure_users_index(index)
        index.delete_all_documents()

        total = 0
        batch = []
        batch_size = 500

        for user in User.objects.all().iterator():
            batch.append(build_user_document(user))
            if len(batch) >= batch_size:
                index.add_documents(batch)
                total += len(batch)
                self.stdout.write(f'Indexados: {total}')
                batch = []

        if batch:
            index.add_documents(batch)
            total += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Reindex concluido: {total} usuarios.'))
