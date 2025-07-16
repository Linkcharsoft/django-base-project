from django_filters import rest_framework as filters

from rest_framework.mixins import (
    RetrieveModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
    ListModelMixin,
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import filters as rest_filters
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django.utils.translation import gettext_lazy as _
from django.db.models import F, Value, CharField
from django.contrib.auth import get_user_model
from django.db.models.functions import Concat

from django_base.base_utils.base_viewsets import BaseGenericViewSet
from users.permissions import HasRegisterCompletePermission
from users.filters import UserFilter
from users.serializers import (
    UserCompleteRegisterSerializer,
    UserListSerializer,
    UserSerializer,
)


class UserViewSet(
    BaseGenericViewSet,
    RetrieveModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
):
    filter_backends = (
        filters.DjangoFilterBackend,
        rest_filters.SearchFilter,
        rest_filters.OrderingFilter,
    )

    search_fields = (
        "full_name",
        "email",
    )

    ordering_fields = (
        "full_name",
        "email",
    )

    ordering = ("-created_at",)

    filterset_class = UserFilter

    permissions = {
        "retrieve": [IsAuthenticated],
        "partial_update": [HasRegisterCompletePermission],
        "complete_register": [IsAuthenticated],
        "toggle-block": [IsAdminUser],
        "destroy": [IsAdminUser],
        "list": [IsAdminUser],
        "default": [HasRegisterCompletePermission],
    }

    serializers = {
        "retrieve": UserSerializer,
        "update": UserSerializer,
        "complete_register": UserCompleteRegisterSerializer,
        "list": UserListSerializer,
        "default": UserSerializer,
    }

    def get_queryset(self):
        queryset = (
            get_user_model()
            .objects.all()
            .prefetch_related("profile")
            .annotate(
                full_name=Concat(
                    F("first_name"),
                    Value(" "),
                    F("last_name"),
                    output_field=CharField(),
                )
            )
        )
        if self.action == "list":
            queryset = queryset.exclude(
                emailaddress__verified=False,
            )
        return queryset

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_parameter = {self.lookup_field: self.kwargs[lookup_url_kwarg]}.get("pk")
        if self.action in ["destroy", "toggle_block"] and (
            lookup_parameter == "me" or lookup_parameter == str(self.request.user.pk)
        ):
            raise NotFound()
        if lookup_parameter == "me" or not self.request.user.is_staff:
            return self.request.user
        return super().get_object()

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

    @action(detail=True, methods=["PATCH"], url_path="toggle-block")
    def toggle_block(self, request, pk=None):
        user = self.get_object()
        if not (is_active := request.data.get("is_active")):
            return Response(
                {"detail": _("is_active field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user.is_active = is_active
            user.save()
        except Exception as e:
            return Response(
                {"detail": _("is_active field should be boolean")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            (
                _("User is blocked")
                if is_active.lower() == "false"
                else _("User is unblocked")
            ),
            status=status.HTTP_200_OK,
        )
