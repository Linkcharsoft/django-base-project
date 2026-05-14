from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_at"] = instance.created_at
        data["updated_at"] = instance.updated_at
        return data
