from rest_framework import serializers

from platform_configurations.models import SystemStatus


class SystemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemStatus
        fields = ("is_operational",)
