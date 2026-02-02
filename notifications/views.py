from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from .services.events import log_notification_clear, log_notification_delete
from .services.queries import get_notification_queryset
from .services.roles import is_super_admin


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

    def get_queryset(self):
        return get_notification_queryset(self.request)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_super_admin(request.user) and instance.recipient_id != request.user.id:
            return Response(
                {
                    'message': 'Usuario sem permissao para deletar notificacoes',
                    'error_code': 'FORBIDDEN',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        log_notification_delete(request, instance)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        user_id = request.query_params.get('user')
        queryset = Notification.objects.all() if is_super_admin(user) else Notification.objects.filter(recipient=user)
        if is_super_admin(user) and user_id:
            queryset = queryset.filter(recipient_id=user_id)
        deleted, _ = queryset.delete()
        log_notification_clear(
            request,
            deleted,
            user_id if is_super_admin(user) else user.id,
        )
        return Response({'deleted': deleted}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        instance = self.get_object()
        if not is_super_admin(request.user) and instance.recipient_id != request.user.id:
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
        if not is_super_admin(request.user) and instance.recipient_id != request.user.id:
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
        queryset = Notification.objects.all() if is_super_admin(user) else Notification.objects.filter(recipient=user)
        user_id = request.query_params.get('user')
        if is_super_admin(user) and user_id:
            queryset = queryset.filter(recipient_id=user_id)
        elif not is_super_admin(user):
            queryset = queryset.filter(recipient=user)
        updated = queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({'updated': updated}, status=status.HTTP_200_OK)
