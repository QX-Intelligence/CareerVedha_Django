from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("entity", "entity_id", "action", "role", "created_at")
    list_filter = ("entity", "role", "action")
