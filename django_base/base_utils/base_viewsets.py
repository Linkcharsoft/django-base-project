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
        return [permission() for permission in self.permissions.get(self.action, [])]


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
        return self.serializers.get(self.action, None)


class BaseGenericViewSetMixin(
    NoPutViewSetMixin,
    ViewSetPermissionMixin,
    ViewSetSerializerMixin,
    GenericViewSet,
):
    pass


class BaseReadOnlyModelViewSetMixin(
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