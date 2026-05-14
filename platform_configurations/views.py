from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from platform_configurations.models import SystemStatus
from platform_configurations.serializers import SystemStatusSerializer


class SystemStatusViewSet(GenericViewSet, mixins.ListModelMixin):
    """Viewset for system status. If the system is not operational,
    the system will return a 503 status code in every endpoint instead of this."""

    queryset = SystemStatus.objects.all()
    serializer_class = SystemStatusSerializer

    @extend_schema(responses=SystemStatusSerializer)
    @action(detail=False, methods=["get"], url_path="is-system-up")
    def system_status(self, request):
        return Response(
            {"is_operational": SystemStatus.get_status().is_operational},
            status=status.HTTP_200_OK,
        )
