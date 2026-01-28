from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'actor',
            'type',
            'payload',
            'created_at',
            'read_at',
        ]
        read_only_fields = fields
