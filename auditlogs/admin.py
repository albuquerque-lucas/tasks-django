from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action', 'entity_type', 'entity_id', 'timestamp')
    list_filter = ('action', 'entity_type', 'timestamp')
    search_fields = ('user__username', 'entity_type', 'entity_id', 'action')
