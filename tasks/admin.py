from django.contrib import admin
from .models import PriorityLevel, Task


@admin.register(PriorityLevel)
class PriorityLevelAdmin(admin.ModelAdmin):
    list_display = ('level', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('level',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'priority_level', 'created_at')
    list_filter = ('status', 'created_at', 'priority_level')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
