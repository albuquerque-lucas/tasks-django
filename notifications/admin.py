from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'actor', 'type', 'created_at', 'read_at')
    list_filter = ('type', 'created_at', 'read_at')
    search_fields = ('recipient__username', 'actor__username', 'type')
