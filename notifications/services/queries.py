from notifications.models import Notification
from .query_params import parse_date_param
from .roles import is_super_admin


def apply_filters(request, queryset, user_only):
    if not user_only:
        user_id = request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(recipient_id=user_id)

    unread = request.query_params.get('unread')
    if unread in {'1', 'true', 'True'}:
        queryset = queryset.filter(read_at__isnull=True)

    notif_type = request.query_params.get('type')
    if notif_type:
        queryset = queryset.filter(type=notif_type)

    date_from = parse_date_param(request.query_params.get('date_from'))
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    date_to = parse_date_param(request.query_params.get('date_to'), end_of_day=True)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    return queryset


def get_notification_queryset(request):
    user = request.user
    if not user.is_authenticated:
        return Notification.objects.none()
    queryset = Notification.objects.all() if is_super_admin(user) else Notification.objects.filter(recipient=user)

    if not is_super_admin(user):
        return apply_filters(request, queryset, user_only=True)

    return apply_filters(request, queryset, user_only=False)
