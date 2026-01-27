from rest_framework import serializers
from .models import Team


class TeamSerializer(serializers.ModelSerializer):
    members_display = serializers.SerializerMethodField()
    managers_display = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'description',
            'members',
            'members_display',
            'managers',
            'managers_display',
        ]

    def get_members_display(self, obj):
        return [
            {
                'id': user.id,
                'name': (f'{user.first_name} {user.last_name}'.strip() or user.username),
            }
            for user in obj.members.all()
        ]

    def get_managers_display(self, obj):
        return [
            {
                'id': user.id,
                'name': (f'{user.first_name} {user.last_name}'.strip() or user.username),
            }
            for user in obj.managers.all()
        ]
