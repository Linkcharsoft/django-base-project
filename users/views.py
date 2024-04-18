from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model


from users.serializers import UserSerializer
from django_base.settings import USE_EXPO_NOTIFICATIONS


class UserViewSet(GenericViewSet, RetrieveModelMixin, UpdateModelMixin):
    permission_classes = [IsAuthenticated]
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if {self.lookup_field: self.kwargs[lookup_url_kwarg]}.get("pk") != "me":
            raise NotFound()
        return self.request.user


    @action(detail=False, url_path="register-device", methods=["POST"]) # Delete if not needed
    def register_device(self, request, *args, **kwargs):
        if not USE_EXPO_NOTIFICATIONS:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        from user_notifications.models import ExpoToken
        user = request.user

        token = request.data.get("token")
        if not token:
            return Response(
                {"detail": "token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        token, created = ExpoToken.objects.get_or_create(user=user, token=token)
        if created:
            tokens = ExpoToken.objects.filter(user=user).order_by("created_at").all()

            if len(tokens) >= 10:
                tokens[0].delete()

        return Response("token saved successfully")

    @action(detail=False, url_path="unregister-device", methods=["POST"]) # Delete if not needed
    def unregister_device(self, request, *args, **kwargs):
        from user_notifications.models import ExpoToken
        if not USE_EXPO_NOTIFICATIONS:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        user = request.user

        token = request.data.get("token")
        if not token:
            raise ParseError("token is required")

        ExpoToken.objects.filter(user=user, token=token).delete()

        return Response("token deleted successfully")