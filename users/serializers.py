from dj_rest_auth.registration.serializers import RegisterSerializer
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework import serializers

from django_base.base_utils.base_serializers import BaseSerializer
from users.models import Profile, User


class ProfileSerializer(BaseSerializer):
    """Serializer del perfil (detalle/registro). Agregá acá los campos
    requeridos para completar el registro."""

    is_register_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = Profile
        fields = ("is_register_complete",)


class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id",)


class UserSerializer(WritableNestedModelSerializer, BaseSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "profile")
        read_only_fields = ("email",)


class UserListSerializer(serializers.ModelSerializer):
    profile = ProfileListSerializer()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "profile")


class UserRegisterSerializer(WritableNestedModelSerializer, BaseSerializer):
    """Serializer del flow de completar registro. first_name y last_name
    pasan a ser requeridos."""

    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "profile")


class CustomRegisterSerializer(RegisterSerializer):
    """Custom Register Serializer
    This serializer extends the default registration serializer to include additional fields
    in the registration process, add them here if needed.
    """

    username = serializers.CharField(required=False, allow_blank=True)
    password2 = serializers.CharField(required=False, write_only=True)
    is_test_user = serializers.BooleanField(default=False)
    # new_field = serializers.BooleanField(required=True)

    def get_cleaned_data(self):
        cleaned_data = super().get_cleaned_data()
        cleaned_data["is_test_user"] = self.validated_data.get("is_test_user", False)
        cleaned_data["username"] = self.validated_data.get("email", "")
        # cleaned_data["new_field"] = self.validated_data.get("new_field", False)
        return cleaned_data

    def _has_phone_field(self):  # TMP: Until dj-rest-auth updates
        return False

    def validate(self, data):
        data["password2"] = data.get("password1", "")  # TMP: Until dj-rest-auth updates
        data = super().validate(data)
        return data

    def save(self, request):
        user = super().save(request)
        self.cleaned_data = self.get_cleaned_data()
        user.is_test_user = self.cleaned_data.get("is_test_user", False)
        # user.new_field = self.cleaned_data.get("new_field")
        user.save()
        return user
