from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet


class NoPutViewSetMixin:
    def update(self, request, *args, **kwargs):
        if self.request.method == "PUT":
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().update(request, *args, **kwargs)


class ViewSetPermissionMixin:
    permissions = {
        "create": [],
        "list": [],
        "retrieve": [],
        "update": [],
        "partial_update": [],
        "destroy": [],
        "default": [],
    }

    extra_permissions = []

    def get_permissions(self):
        permission_classes = self.permissions.get(self.action, self.permissions["default"])
        permission_classes += self.extra_permissions

        assert permission_classes != [], (
            f"Permission classes are empty or not defined for action `{self.action}` "
            f"in '{self.__class__.__name__}', explicitly use [AllowAny] for public "
            f"access or define non empty permission classes for said action."
        )

        return [permission() for permission in permission_classes]


class ViewSetSerializerMixin:
    serializers = {
        "create": None,
        "list": None,
        "retrieve": None,
        "update": None,
        "partial_update": None,
        "destroy": None,
        "default": None,
    }

    def get_serializer_class(self, *args, **kwargs):
        serializer_class = self.serializers.get(self.action, self.serializers["default"])

        assert serializer_class is not None, (
            f"'{self.__class__.__name__}' should either define a serializer class "
            f"for action `{self.action}`, or override the `get_serializer_class()` method."
        )

        return serializer_class


class BaseGenericViewSet(
    NoPutViewSetMixin,
    ViewSetPermissionMixin,
    ViewSetSerializerMixin,
    GenericViewSet,
):
    pass


class BaseReadOnlyModelViewSet(
    ViewSetPermissionMixin,
    ViewSetSerializerMixin,
    ReadOnlyModelViewSet,
):
    pass


class BaseModelViewSet(
    NoPutViewSetMixin,
    ViewSetPermissionMixin,
    ViewSetSerializerMixin,
    ModelViewSet,
):
    pass
