from rest_framework import serializers


class PasswordRecoverySendMailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    request_type = serializers.ChoiceField(
        choices=("reset", "change"), default="reset", required=False
    )


class PasswordRecoveryCheckTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()


class PasswordRecoveryConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class PasswordRecoveryResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
