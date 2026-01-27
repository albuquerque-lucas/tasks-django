from .models import AuditLog


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit_event(request, action, entity_type, entity_id=None, metadata=None, user_override=None):
    user = user_override or getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None

    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id='' if entity_id is None else str(entity_id),
        metadata=metadata or {},
        ip=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
