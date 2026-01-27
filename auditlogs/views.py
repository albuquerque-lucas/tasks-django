from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AuditLog
from .serializers import AuditLogSerializer
from .utils import log_audit_event


class AuditLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'delete', 'head', 'options']

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
