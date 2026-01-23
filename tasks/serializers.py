from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    user_display = serializers.StringRelatedField(source='user', read_only=True)
    
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
            'priority',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_display']
        extra_kwargs = {
            'user': {'required': False}
        }
    
    def validate_title(self, value):
        """Valida se título não está vazio"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Título não pode estar vazio.')
        if len(value) > 200:
            raise serializers.ValidationError('Título não pode ter mais de 200 caracteres.')
        return value
    
    def validate_status(self, value):
        """Valida se status é válido"""
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f'Status deve ser um de: {", ".join(valid_statuses)}'
            )
        return value
    
    def validate_priority(self, value):
        """Valida se prioridade é válida"""
        if value < 0 or value > 10:
            raise serializers.ValidationError('Prioridade deve estar entre 0 e 10.')
        return value
