from rest_framework import serializers
from django.contrib.auth import get_user_model

from notifications.services.presence import is_user_online

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'bio',
            'phone',
            'notifications_last_seen_at',
        ]
        read_only_fields = ['id', 'notifications_last_seen_at']


class UserDetailSerializer(UserSerializer):
    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + ['date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login', 'notifications_last_seen_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'password2',
        ]

    def validate_username(self, value):
        """Valida se username já existe"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Este username já está em uso.')
        if len(value) < 3:
            raise serializers.ValidationError('Username deve ter no mínimo 3 caracteres.')
        return value

    def validate_email(self, value):
        """Valida se email já existe"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este email já está em uso.')
        return value

    def validate(self, data):
        """Valida se as senhas são iguais"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                'password2': 'As senhas não coincidem.'
            })
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserPresenceSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'last_seen_at',
            'is_online',
        ]
        read_only_fields = fields

    def get_is_online(self, obj):
        online_map = self.context.get('online_map')
        if online_map is not None:
            return bool(online_map.get(obj.id))
        return is_user_online(obj.id)

