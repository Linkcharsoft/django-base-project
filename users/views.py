from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _


from django_base.base_utils.base_viewsets import BaseGenericViewSet
from users.serializers import UserCompleteRegisterSerializer, UserSerializer


class UserViewSet(BaseGenericViewSet, RetrieveModelMixin, UpdateModelMixin):
    queryset = get_user_model().objects.all()

    permissions = {
        "retrieve": [IsAuthenticated],
        "update": [IsAuthenticated],
        "complete_register": [IsAuthenticated],
        "default": [IsAuthenticated],
    }

    serializers = {
        "retrieve": UserSerializer,
        "update": UserSerializer,
        "complete_register": UserCompleteRegisterSerializer,
        "default": UserSerializer,
    }

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if {self.lookup_field: self.kwargs[lookup_url_kwarg]}.get("pk") != "me":
            raise NotFound()
        return self.request.user

    @action(detail=False, methods=["PATCH"], url_path="complete-register")
    def complete_register(self, request):
        user = request.user

        if user.profile.is_register_complete:
            return Response(_("Register already completed"), status=400)

        serializer = self.get_serializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        user.profile.complete_register()

        return Response(_("Register completed"), status=status.HTTP_200_OK)
