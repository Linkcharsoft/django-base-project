from django.contrib import admin
from platform_configurations.models import SystemStatus


@admin.register(SystemStatus)
class SystemStatusAdmin(admin.ModelAdmin):
    list_display = ("pk", "is_operational")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
