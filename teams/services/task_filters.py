from django.db.models import Q


def apply_team_task_search_filter(queryset, search_term):
    search_filter = (
        Q(title__icontains=search_term)
        | Q(description__icontains=search_term)
        | Q(status__icontains=search_term)
        | Q(priority_level__name__icontains=search_term)
        | Q(user__username__icontains=search_term)
        | Q(user__email__icontains=search_term)
        | Q(user__first_name__icontains=search_term)
        | Q(user__last_name__icontains=search_term)
    )
    if search_term.isdigit():
        search_filter |= Q(id=int(search_term))
        search_filter |= Q(priority_level__level=int(search_term))
    return queryset.filter(search_filter)
