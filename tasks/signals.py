from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Task
from safetodo.services.meili import upsert_task, delete_task


@receiver(post_save, sender=Task)
def task_saved(sender, instance, **kwargs):
    upsert_task(instance)


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
    delete_task(instance.id)
