from auditlogs.utils import log_audit_event


def log_notification_delete(request, instance):
    deleted_data = {
        'type': instance.type,
        'recipient_id': instance.recipient_id,
        'actor_id': instance.actor_id,
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
    }
    log_audit_event(
        request,
        action='notification.delete',
        entity_type='Notification',
        entity_id=instance.id,
        metadata={'deleted_notification': deleted_data},
    )
    return deleted_data


def log_notification_clear(request, deleted, user_id):
    log_audit_event(
        request,
        action='notification.clear',
        entity_type='Notification',
        entity_id='',
        metadata={'deleted': deleted, 'user_id': user_id},
    )
