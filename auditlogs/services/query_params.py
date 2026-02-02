from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


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


def get_meili_sort(ordering, ordering_fields):
    if not ordering:
        return ['id:desc']
    ordering_fields = set(ordering_fields or [])
    for item in ordering:
        field = item.lstrip('-')
        if field in ordering_fields:
            direction = 'desc' if item.startswith('-') else 'asc'
            return [f'{field}:{direction}']
    return ['id:desc']


def build_page_link(request, page):
    params = request.query_params.copy()
    params['page'] = page
    return request.build_absolute_uri(f'?{params.urlencode()}')


def parse_date_param(value, end_of_day=False):
    if not value:
        return None
    parsed_dt = parse_datetime(value)
    if parsed_dt:
        if timezone.is_naive(parsed_dt):
            return timezone.make_aware(parsed_dt)
        return parsed_dt
    parsed_date = parse_date(value)
    if not parsed_date:
        return None
    if end_of_day:
        parsed_dt = timezone.datetime.combine(
            parsed_date,
            timezone.datetime.max.time(),
        )
    else:
        parsed_dt = timezone.datetime.combine(
            parsed_date,
            timezone.datetime.min.time(),
        )
    return timezone.make_aware(parsed_dt) if timezone.is_naive(parsed_dt) else parsed_dt
