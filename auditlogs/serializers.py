from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'action',
            'entity_type',
            'entity_id',
            'metadata',
            'timestamp',
            'ip',
            'user_agent',
        ]
        read_only_fields = fields
