from auditlogs.utils import log_audit_event


def log_auditlog_delete(request, instance):
    deleted_data = {
        'action': instance.action,
        'entity_type': instance.entity_type,
        'entity_id': instance.entity_id,
        'user_id': instance.user_id,
        'timestamp': instance.timestamp.isoformat() if instance.timestamp else None,
    }
    log_audit_event(
        request,
        action='auditlog.delete',
        entity_type='AuditLog',
        entity_id=instance.id,
        metadata={'deleted_log': deleted_data},
    )
    return deleted_data


def log_auditlog_clear(request, deleted, user_id):
    log_audit_event(
        request,
        action='auditlog.clear',
        entity_type='AuditLog',
        entity_id='',
        metadata={'deleted': deleted, 'user_id': user_id},
    )
