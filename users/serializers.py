from drf_writable_nested.serializers import WritableNestedModelSerializer
from drf_writable_nested.mixins import UniqueFieldsMixin

from rest_framework import serializers

from django_base.base_utils.base_serializers import BaseSoftDeleteSerializer

from users.models import User, Profile


class UserProfileSerializer(BaseSoftDeleteSerializer):
    class Meta:
        model = Profile
        exclude = ["user", "created_at", "updated_at", "deleted", "deleted_at"]


class UserSerializer(WritableNestedModelSerializer, BaseSoftDeleteSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "profile")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["email"] = instance.email
        return data
