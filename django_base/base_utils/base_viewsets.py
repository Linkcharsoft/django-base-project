from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet, ModelViewSet


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
    }

    def get_permissions(self):
        permission_classes = self.permissions.get(self.action, [])

        assert permission_classes != [], (
            "Permission classes are empty or not defined for action `%s` in '%s',"
            "explicitly use [AllowAny] for public access or"
            "define non empty permission classes for said action."
            % (self.action, self.__class__.__name__)
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
    }

    def get_serializer_class(self, *args, **kwargs):
        serializer_class = self.serializers.get(self.action, None)

        assert serializer_class is not None, (
            "'%s' should either define a serializer class for action `%s`, "
            "or override the `get_serializer_class()` method."
            % (self.__class__.__name__, self.action)
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
