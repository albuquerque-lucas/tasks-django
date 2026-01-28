from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def notify(recipient, type, payload, actor=None):
    if not recipient:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        type=type,
        payload=payload or {},
    )
    channel_layer = get_channel_layer()
    try:
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'user_{recipient.id}',
                {
                    'type': 'notification.created',
                    'notification_id': notification.id,
                },
            )
    except Exception:
        # Nao interromper criacao da notificacao se o broadcast falhar
        pass
    return notification
