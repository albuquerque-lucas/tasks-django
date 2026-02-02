import math
from django.db.models import Case, IntegerField, When
from rest_framework.response import Response
from safetodo.services.meili import search_auditlogs
from .query_params import build_page_link, get_meili_sort
from .queries import apply_ordering, apply_search_filter


def search_auditlogs_meili(
    *,
    request,
    queryset,
    serializer_getter,
    ordering,
    ordering_fields,
    page,
    page_size,
    search_term,
    filters,
):
    meili_sort = get_meili_sort(ordering, ordering_fields)
    offset = (page - 1) * page_size

    is_numeric = search_term.isdigit()
    filter_clauses = []
    if is_numeric:
        filter_clauses.append(f'id = {int(search_term)}')
    user_id = filters.get('user')
    if user_id and user_id.isdigit():
        filter_clauses.append(f'user_id = {int(user_id)}')
    entity_type = filters.get('entity_type')
    if entity_type:
        filter_clauses.append(f'entity_type = \"{entity_type}\"')
    action = filters.get('action')
    if action:
        filter_clauses.append(f'action = \"{action}\"')
    filter_value = ' AND '.join(filter_clauses) if filter_clauses else None
    query = '' if is_numeric else search_term

    meili_result = search_auditlogs(
        query=query,
        offset=offset,
        limit=page_size,
        sort=meili_sort,
        filter_value=filter_value,
    )
    hits = meili_result.get('hits', [])
    total = meili_result.get('estimatedTotalHits') or meili_result.get('nbHits') or 0
    ids = [item.get('id') for item in hits if item.get('id') is not None]
    if not ids:
        results = []
    else:
        preserved = Case(
            *[When(id=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField(),
        )
        results = queryset.filter(id__in=ids).order_by(preserved)

    serializer = serializer_getter(results, many=True)
    total_pages = math.ceil(total / page_size) if page_size else 1
    next_link = build_page_link(request, page + 1) if page < total_pages else None
    prev_link = build_page_link(request, page - 1) if page > 1 else None
    response = Response(
        {
            'count': total,
            'next': next_link,
            'previous': prev_link,
            'results': serializer.data,
        }
    )
    response['X-Search-Provider'] = 'meili'
    return response


def fallback_search(
    *,
    request,
    queryset,
    serializer_getter,
    paginator,
    ordering,
    ordering_fields,
    default_ordering,
    search_term,
    provider='db',
):
    queryset = apply_search_filter(queryset, search_term)
    queryset = apply_ordering(queryset, ordering, ordering_fields, default_ordering)

    page_data = paginator.paginate_queryset(queryset, request)
    response = paginator.get_paginated_response(
        serializer_getter(page_data, many=True).data
    )
    response['X-Search-Provider'] = provider
    return response
