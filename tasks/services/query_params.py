def parse_page_params(request, default_page=1, default_page_size=10, max_page_size=500):
    try:
        page = int(request.query_params.get('page', default_page))
    except ValueError:
        page = default_page
    try:
        page_size = int(request.query_params.get('page_size', default_page_size))
    except ValueError:
        page_size = default_page_size
    page = max(1, page)
    page_size = max(1, min(page_size, max_page_size))
    return page, page_size


def get_ordering(request, default_ordering=None):
    ordering_param = request.query_params.get('ordering')
    if ordering_param:
        return [item.strip() for item in ordering_param.split(',') if item.strip()]
    return list(default_ordering or [])


def get_meili_sort(ordering, ordering_fields, mapping=None):
    if not ordering:
        return ['id:desc']
    ordering_fields = set(ordering_fields or [])
    mapping = mapping or {}
    for item in ordering:
        field = item.lstrip('-')
        if field in ordering_fields:
            meili_field = mapping.get(field, field)
            direction = 'desc' if item.startswith('-') else 'asc'
            return [f'{meili_field}:{direction}']
    return ['id:desc']


def build_page_link(request, page):
    params = request.query_params.copy()
    params['page'] = page
    return request.build_absolute_uri(f'?{params.urlencode()}')


def apply_search_filter(queryset, search_term):
    from django.db.models import Q

    search_filter = (
        Q(title__icontains=search_term)
        | Q(description__icontains=search_term)
        | Q(status__icontains=search_term)
        | Q(priority_level__name__icontains=search_term)
        | Q(user__username__icontains=search_term)
        | Q(user__email__icontains=search_term)
        | Q(user__first_name__icontains=search_term)
        | Q(user__last_name__icontains=search_term)
        | Q(team__name__icontains=search_term)
    )
    if search_term.isdigit():
        search_filter |= Q(id=int(search_term))
        search_filter |= Q(priority_level__level=int(search_term))
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
