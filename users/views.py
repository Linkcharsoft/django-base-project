from django.contrib.auth import get_user_model
from django.db.models import CharField, F, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import filters as rest_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import (
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from django_base.base_utils.base_viewsets import BaseGenericViewSet
from users.filters import UserFilter
from users.permissions import HasRegisterCompletePermission
from users.serializers import (
    DetailMessageSerializer,
    ToggleBlockSerializer,
    UserListSerializer,
    UserRegisterSerializer,
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
        "toggle_block": [IsAdminUser],
        "destroy": [IsAdminUser],
        "list": [IsAdminUser],
        "delete_test_users": [AllowAny],
        "default": [HasRegisterCompletePermission],
    }

    serializers = {
        "retrieve": UserSerializer,
        "update": UserSerializer,
        "complete_register": UserRegisterSerializer,
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
        """Resolve the target user with ownership + safety guards.

        Three policies baked in here, all surprising to a cold reader:
        - `me` is a sentinel for the current user's pk (frontends call
            `GET /users/me/` instead of looking up their own id first).
        - Non-staff requests always resolve to `request.user` regardless
            of the pk in the URL — they cannot read or write other users.
        - Admins cannot target themselves with `destroy` or `toggle_block`
            (404), to prevent accidental self-lockout.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_parameter = {self.lookup_field: self.kwargs[lookup_url_kwarg]}.get("pk")
        if self.action in ["destroy", "toggle_block"] and (
            lookup_parameter == "me" or lookup_parameter == str(self.request.user.pk)
        ):
            raise NotFound()
        if lookup_parameter == "me" or not self.request.user.is_staff:
            return self.request.user
        return super().get_object()

    @extend_schema(
        request=UserRegisterSerializer,
        responses={
            200: DetailMessageSerializer,
            400: DetailMessageSerializer,
        },
        description=(
            "Marks the authenticated user's profile as register-complete. "
            "Returns a `detail` message and never the user object."
        ),
    )
    @action(detail=False, methods=["PATCH"], url_path="complete-register")
    def complete_register(self, request):
        user = request.user

        if user.profile.is_register_complete:
            return Response(
                {"detail": _("Register already completed")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        user.profile.complete_register()

        return Response(
            {"detail": _("Register completed")},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=ToggleBlockSerializer,
        responses={
            200: DetailMessageSerializer,
            400: DetailMessageSerializer,
        },
        description=(
            "Admin-only: toggle `is_active` on the target user. The response "
            "is a `detail` message, not the user object."
        ),
    )
    @action(detail=True, methods=["PATCH"], url_path="toggle-block")
    def toggle_block(self, request, pk=None):
        user = self.get_object()
        is_active = request.data.get("is_active")

        if is_active is None:
            return Response(
                {"detail": _("is_active field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(is_active, str):
            if is_active.lower() in ("true", "1"):
                is_active = True
            elif is_active.lower() in ("false", "0"):
                is_active = False
            else:
                return Response(
                    {"detail": _("is_active field should be boolean")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not isinstance(is_active, bool):
            return Response(
                {"detail": _("is_active field should be boolean")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = is_active
        user.save(update_fields=["is_active"])

        return Response(
            {"detail": _("User is unblocked") if is_active else _("User is blocked")},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=None,
        responses={204: DetailMessageSerializer},
        description=(
            "Bulk-delete every user flagged `is_test_user=True`. Returns 204 "
            "with a `detail` message. Intended for e2e teardown."
        ),
    )
    @action(detail=False, methods=["DELETE"], url_path="delete-test-users")
    def delete_test_users(self, request):
        get_user_model().objects.filter(is_test_user=True).delete()
        return Response(
            {"detail": _("Test users deleted")},
            status=status.HTTP_204_NO_CONTENT,
        )
