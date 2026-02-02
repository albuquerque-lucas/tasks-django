from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AuditLog
from .serializers import AuditLogSerializer
from .services.events import log_auditlog_clear, log_auditlog_delete
from .services.query_params import (
    get_ordering,
    parse_page_params,
)
from .services.queries import get_auditlog_queryset
from .services.roles import is_admin, is_super_admin
from .services.search import fallback_search, search_auditlogs_meili


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

    def get_queryset(self):
        return get_auditlog_queryset(self.request)

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        user = request.user
        if not is_admin(user):
            return fallback_search(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                paginator=self.paginator,
                ordering=get_ordering(request, self.ordering),
                ordering_fields=self.ordering_fields,
                default_ordering=self.ordering,
                search_term=search_term,
                provider='db',
            )

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from or date_to:
            return fallback_search(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                paginator=self.paginator,
                ordering=get_ordering(request, self.ordering),
                ordering_fields=self.ordering_fields,
                default_ordering=self.ordering,
                search_term=search_term,
                provider='db',
            )

        page, page_size = parse_page_params(request)
        ordering = get_ordering(request, self.ordering)
        try:
            return search_auditlogs_meili(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                ordering=ordering,
                ordering_fields=self.ordering_fields,
                page=page,
                page_size=page_size,
                search_term=search_term,
                filters={
                    'user': request.query_params.get('user'),
                    'entity_type': request.query_params.get('entity_type'),
                    'action': request.query_params.get('action'),
                },
            )
        except Exception:
            return fallback_search(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                paginator=self.paginator,
                ordering=ordering,
                ordering_fields=self.ordering_fields,
                default_ordering=self.ordering,
                search_term=search_term,
                provider='db',
            )

    def destroy(self, request, *args, **kwargs):
        if not is_super_admin(request.user):
            return Response(
                {
                    'message': 'Usuario sem permissao para deletar logs',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        log_auditlog_delete(request, instance)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete', 'post'])
    def clear(self, request):
        if not is_super_admin(request.user):
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
        log_auditlog_clear(request, deleted, user_id)
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)
