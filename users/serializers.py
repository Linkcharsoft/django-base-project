from drf_writable_nested.serializers import WritableNestedModelSerializer

from rest_framework import serializers

from dj_rest_auth.registration.serializers import RegisterSerializer

from django.utils.translation import gettext_lazy as _

from django_base.base_utils.base_serializers import BaseSerializer
from users.models import User, Profile


class UserProfileCompleteSerializer(BaseSerializer):
    """USE THIS FOR USER PROFILE COMPLETE REGISTRATION
    Serializer for completing user profile registration.
    This serializer is used to collect all necessary information for a user profile
    when they are completing their registration.
    """

    is_register_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "is_register_complete",
            # add other fields that are required for profile completion here
        ]


class UserCompleteRegisterSerializer(WritableNestedModelSerializer, BaseSerializer):
    """USE THIS FOR USER COMPLETE REGISTRATION
    Serializer for completing user profile registration.
    This serializer is used to collect all necessary information for a user profile
    when they are completing their registration.
    """

    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    profile = UserProfileCompleteSerializer()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "profile",
            # add other fields that are required for user completion here
        )


class UserProfileSerializer(BaseSerializer):
    is_register_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = Profile
        fields = ("is_register_complete",)


class UserProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id",)


class UserSerializer(WritableNestedModelSerializer, BaseSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "profile")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["email"] = instance.email
        return data


class UserListSerializer(serializers.ModelSerializer):
    profile = UserProfileListSerializer()

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "profile",
        )


class CustomRegisterSerializer(RegisterSerializer):
    """Custom Register Serializer
    This serializer extends the default registration serializer to include additional fields
    in the registration process, add them here if needed.
    """

    password2 = serializers.CharField(required=False, write_only=True)
    is_test_user = serializers.BooleanField(default=False)
    # new_field = serializers.BooleanField(required=True)

    def get_cleaned_data(self):
        cleaned_data = super().get_cleaned_data()
        cleaned_data["is_test_user"] = self.validated_data.get("is_test_user", False)
        # cleaned_data["new_field"] = self.validated_data.get("new_field", False)
        return cleaned_data

    def validate(self, data):
        return data

    def save(self, request):
        user = super().save(request)
        self.cleaned_data = self.get_cleaned_data()
        user.is_test_user = self.cleaned_data.get("is_test_user", False)
        # user.new_field = self.cleaned_data.get("new_field")
        user.save()
        return user
