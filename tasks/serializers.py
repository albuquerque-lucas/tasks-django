from rest_framework import serializers
from .models import PriorityLevel, Task


class PriorityLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorityLevel
        fields = [
            'id',
            'level',
            'name',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskSerializer(serializers.ModelSerializer):
    user_display = serializers.StringRelatedField(source='user', read_only=True)
    priority_level_display = serializers.CharField(
        source='priority_level.name',
        read_only=True
    )

    class Meta:
        model = Task
        fields = [
            'id',
            'user',
            'user_display',
            'title',
            'description',
            'status',
            'due_date',
            'priority_level',
            'priority_level_display',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_display']
        extra_kwargs = {
            'user': {'required': False},
            'priority_level': {'required': False, 'allow_null': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is None and 'status' in self.fields:
            self.fields['status'].read_only = True

    def validate_title(self, value):
        """Valida se titulo nao esta vazio"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Titulo nao pode estar vazio.')
        if len(value) > 200:
            raise serializers.ValidationError('Titulo nao pode ter mais de 200 caracteres.')
        return value

    def validate_status(self, value):
        """Valida se status e valido"""
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f'Status deve ser um de: {", ".join(valid_statuses)}'
            )
        return value

    def validate_priority_level(self, value):
        """Valida se nivel de prioridade esta ativo"""
        if value is None:
            return value
        if not value.is_active:
            raise serializers.ValidationError('Nivel de prioridade inativo.')
        return value
