from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Team
from safetodo.services.meili import upsert_team, delete_team


@receiver(post_save, sender=Team)
def team_saved(sender, instance, **kwargs):
    upsert_team(instance)


@receiver(post_delete, sender=Team)
def team_deleted(sender, instance, **kwargs):
    delete_team(instance.id)
