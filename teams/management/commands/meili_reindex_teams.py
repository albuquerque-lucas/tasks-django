from django.core.management.base import BaseCommand, CommandError

from safetodo.services.meili import (
    build_team_document,
    ensure_teams_index,
    get_teams_index,
)
from teams.models import Team


class Command(BaseCommand):
    help = 'Reindexa equipes no Meilisearch'

    def handle(self, *args, **options):
        index = get_teams_index()
        if index is None:
            raise CommandError('Meilisearch nao configurado (MEILI_HOST).')

        ensure_teams_index(index)
        index.delete_all_documents()

        total = 0
        batch = []
        batch_size = 500

        for team in Team.objects.all().iterator():
            batch.append(build_team_document(team))
            if len(batch) >= batch_size:
                index.add_documents(batch, primary_key='id')
                total += len(batch)
                self.stdout.write(f'Indexados: {total}')
                batch = []

        if batch:
            index.add_documents(batch, primary_key='id')
            total += len(batch)

        self.stdout.write(self.style.SUCCESS(f'Reindex concluido: {total} equipes.'))
