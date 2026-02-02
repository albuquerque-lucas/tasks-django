from django.db.models import Q
from auditlogs.models import AuditLog
from .query_params import parse_date_param
from .roles import is_admin


def get_auditlog_queryset(request):
    user = request.user
    if not user.is_authenticated:
        return AuditLog.objects.none()
    queryset = AuditLog.objects.all() if is_admin(user) else AuditLog.objects.filter(user=user)

    if not is_admin(user):
        return queryset

    user_id = request.query_params.get('user')
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    entity_type = request.query_params.get('entity_type')
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)

    action = request.query_params.get('action')
    if action:
        queryset = queryset.filter(action=action)

    date_from = parse_date_param(request.query_params.get('date_from'))
    if date_from:
        queryset = queryset.filter(timestamp__gte=date_from)

    date_to = parse_date_param(request.query_params.get('date_to'), end_of_day=True)
    if date_to:
        queryset = queryset.filter(timestamp__lte=date_to)

    return queryset


def apply_search_filter(queryset, search_term):
    search_filter = (
        Q(action__icontains=search_term)
        | Q(entity_type__icontains=search_term)
        | Q(entity_id__icontains=search_term)
        | Q(user__username__icontains=search_term)
        | Q(user__email__icontains=search_term)
        | Q(user__first_name__icontains=search_term)
        | Q(user__last_name__icontains=search_term)
    )
    if search_term.isdigit():
        search_filter |= Q(id=int(search_term))
    return queryset.filter(search_filter)


def apply_ordering(queryset, ordering, ordering_fields, default_ordering=None):
    valid_ordering = []
    ordering_fields = set(ordering_fields or [])
    for item in ordering:
        field = item.lstrip('-')
        if field in ordering_fields:
            valid_ordering.append(item)
    if valid_ordering:
        return queryset.order_by(*valid_ordering)
    if default_ordering:
        return queryset.order_by(*default_ordering)
    return queryset
