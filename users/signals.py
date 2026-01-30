from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import User
from safetodo.services.meili import upsert_user, delete_user


@receiver(post_save, sender=User)
def user_saved(sender, instance, **kwargs):
    upsert_user(instance)


@receiver(post_delete, sender=User)
def user_deleted(sender, instance, **kwargs):
    delete_user(instance.id)
