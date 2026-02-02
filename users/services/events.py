from auditlogs.utils import log_audit_event


def log_user_register(request, user):
    log_audit_event(
        request,
        action='user.register',
        entity_type='User',
        entity_id=user.id,
        metadata={
            'username': user.username,
            'email': user.email,
        },
        user_override=user,
    )


def log_user_create(request, user):
    log_audit_event(
        request,
        action='user.create',
        entity_type='User',
        entity_id=user.id,
        metadata={
            'username': user.username,
            'email': user.email,
        },
    )


def log_user_update(request, user, before, after):
    changes = {
        key: {'from': before[key], 'to': after[key]}
        for key in before
        if before[key] != after[key]
    }
    if changes:
        log_audit_event(
            request,
            action='user.update',
            entity_type='User',
            entity_id=user.id,
            metadata={'changes': changes},
        )
    return changes


def log_user_delete(request, user):
    log_audit_event(
        request,
        action='user.delete',
        entity_type='User',
        entity_id=user.id,
        metadata={
            'username': user.username,
            'email': user.email,
        },
    )
