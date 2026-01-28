from .models import Notification


def notify(recipient, type, payload, actor=None):
    if not recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        type=type,
        payload=payload or {},
    )
