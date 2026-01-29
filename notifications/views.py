from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from auditlogs.utils import log_audit_event
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'delete', 'head', 'options', 'post']
    ordering_fields = ['id', 'created_at', 'type', 'read_at']
    ordering = ['-created_at', '-id']

    def _is_super_admin(self, user):
        return user.is_superuser or user.groups.filter(name='super_admin').exists()

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
            return Notification.objects.none()
        queryset = Notification.objects.all() if self._is_super_admin(user) else Notification.objects.filter(recipient=user)

        if not self._is_super_admin(user):
            return self._apply_filters(queryset, user_only=True)

        return self._apply_filters(queryset, user_only=False)

    def _apply_filters(self, queryset, user_only):
        if not user_only:
            user_id = self.request.query_params.get('user')
            if user_id:
                queryset = queryset.filter(recipient_id=user_id)

        unread = self.request.query_params.get('unread')
        if unread in {'1', 'true', 'True'}:
            queryset = queryset.filter(read_at__isnull=True)

        notif_type = self.request.query_params.get('type')
        if notif_type:
            queryset = queryset.filter(type=notif_type)

        date_from = self._parse_date_param(self.request.query_params.get('date_from'))
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = self._parse_date_param(self.request.query_params.get('date_to'), end_of_day=True)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._is_super_admin(request.user) and instance.recipient_id != request.user.id:
            return Response(
                {
                    'message': 'Usuario sem permissao para deletar notificacoes',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        deleted_data = {
            'type': instance.type,
            'recipient_id': instance.recipient_id,
            'actor_id': instance.actor_id,
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
        }
        instance.delete()
        log_audit_event(
            request,
            action='notification.delete',
            entity_type='Notification',
            entity_id=instance.id,
            metadata={'deleted_notification': deleted_data},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        user_id = request.query_params.get('user')
        queryset = Notification.objects.all() if self._is_super_admin(user) else Notification.objects.filter(recipient=user)
        if self._is_super_admin(user) and user_id:
            queryset = queryset.filter(recipient_id=user_id)
        deleted, _ = queryset.delete()
        log_audit_event(
            request,
            action='notification.clear',
            entity_type='Notification',
            entity_id='',
            metadata={'deleted': deleted, 'user_id': user_id if self._is_super_admin(user) else user.id},
        )
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        instance = self.get_object()
        if not self._is_super_admin(request.user) and instance.recipient_id != request.user.id:
            return Response(
                {
                    'message': 'Usuario sem permissao para alterar notificacoes',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.read_at = timezone.now()
        instance.save(update_fields=['read_at'])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['post'])
    def unread(self, request, pk=None):
        instance = self.get_object()
        if not self._is_super_admin(request.user) and instance.recipient_id != request.user.id:
            return Response(
                {
                    'message': 'Usuario sem permissao para alterar notificacoes',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.read_at = None
        instance.save(update_fields=['read_at'])
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        queryset = Notification.objects.all() if self._is_super_admin(user) else Notification.objects.filter(recipient=user)
        user_id = request.query_params.get('user')
        if self._is_super_admin(user) and user_id:
            queryset = queryset.filter(recipient_id=user_id)
        elif not self._is_super_admin(user):
            queryset = queryset.filter(recipient=user)
        updated = queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({'updated': updated}, status=status.HTTP_200_OK)
