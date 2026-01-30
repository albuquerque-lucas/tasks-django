import math
from django.db.models import Case, IntegerField, Q, When
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AuditLog
from .serializers import AuditLogSerializer
from .utils import log_audit_event
from safetodo.services.meili import search_auditlogs


class AuditLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'delete', 'head', 'options']
    ordering_fields = ['id', 'timestamp', 'action', 'entity_type', 'entity_id']
    ordering = ['-timestamp', '-id']

    def _parse_page_params(self, request):
        try:
            page = int(request.query_params.get('page', 1))
        except ValueError:
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 10))
        except ValueError:
            page_size = 10
        page = max(1, page)
        page_size = max(1, min(page_size, 500))
        return page, page_size

    def _get_ordering(self, request):
        ordering_param = request.query_params.get('ordering')
        if ordering_param:
            return [item.strip() for item in ordering_param.split(',') if item.strip()]
        return list(self.ordering or [])

    def _get_meili_sort(self, ordering):
        if not ordering:
            return ['id:desc']
        ordering_fields = set(self.ordering_fields or [])
        for item in ordering:
            field = item.lstrip('-')
            if field in ordering_fields:
                direction = 'desc' if item.startswith('-') else 'asc'
                return [f'{field}:{direction}']
        return ['id:desc']

    def _build_page_link(self, request, page):
        params = request.query_params.copy()
        params['page'] = page
        return request.build_absolute_uri(f'?{params.urlencode()}')

    def _is_super_admin(self, user):
        return user.is_superuser or user.groups.filter(name='super_admin').exists()

    def _is_company_admin(self, user):
        return user.groups.filter(name='company_admin').exists()

    def _is_admin(self, user):
        return self._is_super_admin(user) or self._is_company_admin(user)

    def _parse_date_param(self, value, end_of_day=False):
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

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return AuditLog.objects.none()
        queryset = AuditLog.objects.all() if self._is_admin(user) else AuditLog.objects.filter(user=user)

        if not self._is_admin(user):
            return queryset

        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        date_from = self._parse_date_param(self.request.query_params.get('date_from'))
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)

        date_to = self._parse_date_param(self.request.query_params.get('date_to'), end_of_day=True)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)

        return queryset

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        user = request.user
        if not self._is_admin(user):
            return self._fallback_search(request, search_term)

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from or date_to:
            return self._fallback_search(request, search_term)

        page, page_size = self._parse_page_params(request)
        ordering = self._get_ordering(request)
        meili_sort = self._get_meili_sort(ordering)
        offset = (page - 1) * page_size

        is_numeric = search_term.isdigit()
        filter_clauses = []
        if is_numeric:
            filter_clauses.append(f'id = {int(search_term)}')
        user_id = request.query_params.get('user')
        if user_id and user_id.isdigit():
            filter_clauses.append(f'user_id = {int(user_id)}')
        entity_type = request.query_params.get('entity_type')
        if entity_type:
            filter_clauses.append(f'entity_type = \"{entity_type}\"')
        action = request.query_params.get('action')
        if action:
            filter_clauses.append(f'action = \"{action}\"')
        filter_value = ' AND '.join(filter_clauses) if filter_clauses else None
        query = '' if is_numeric else search_term

        try:
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
                results = self.get_queryset().filter(id__in=ids).order_by(preserved)

            serializer = self.get_serializer(results, many=True)
            total_pages = math.ceil(total / page_size) if page_size else 1
            next_link = self._build_page_link(request, page + 1) if page < total_pages else None
            prev_link = self._build_page_link(request, page - 1) if page > 1 else None
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
        except Exception:
            return self._fallback_search(request, search_term, provider='db')

    def _fallback_search(self, request, search_term, provider='db'):
        queryset = self.get_queryset()
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
        queryset = queryset.filter(search_filter)

        ordering = self._get_ordering(request)
        valid_ordering = []
        ordering_fields = set(self.ordering_fields or [])
        for item in ordering:
            field = item.lstrip('-')
            if field in ordering_fields:
                valid_ordering.append(item)
        if valid_ordering:
            queryset = queryset.order_by(*valid_ordering)
        elif self.ordering:
            queryset = queryset.order_by(*self.ordering)

        paginator = self.paginator
        page_data = paginator.paginate_queryset(queryset, request)
        response = paginator.get_paginated_response(
            self.get_serializer(page_data, many=True).data
        )
        response['X-Search-Provider'] = provider
        return response

    def destroy(self, request, *args, **kwargs):
        if not self._is_super_admin(request.user):
            return Response(
                {
                    'message': 'Usuario sem permissao para deletar logs',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        deleted_data = {
            'action': instance.action,
            'entity_type': instance.entity_type,
            'entity_id': instance.entity_id,
            'user_id': instance.user_id,
            'timestamp': instance.timestamp.isoformat() if instance.timestamp else None,
        }
        instance.delete()
        log_audit_event(
            request,
            action='auditlog.delete',
            entity_type='AuditLog',
            entity_id=instance.id,
            metadata={'deleted_log': deleted_data},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete', 'post'])
    def clear(self, request):
        if not self._is_super_admin(request.user):
            return Response(
                {
                    'message': 'Usuario sem permissao para limpar logs',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        user_id = request.query_params.get('user')
        queryset = self.get_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        deleted, _ = queryset.delete()
        log_audit_event(
            request,
            action='auditlog.clear',
            entity_type='AuditLog',
            entity_id='',
            metadata={'deleted': deleted, 'user_id': user_id},
        )
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)
