from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AuditLog
from safetodo.services.meili import upsert_auditlog, delete_auditlog


@receiver(post_save, sender=AuditLog)
def auditlog_saved(sender, instance, **kwargs):
    upsert_auditlog(instance)


@receiver(post_delete, sender=AuditLog)
def auditlog_deleted(sender, instance, **kwargs):
    delete_auditlog(instance.id)
