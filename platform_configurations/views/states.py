from django_filters import rest_framework as filters

from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework import filters as rest_filters

from django.conf import settings

from platform_configurations import models
from platform_configurations.serializers import states



if settings.INCLUDE_LOCATION and models.get_abstract_state_model():
        class StateViewSet(ReadOnlyModelViewSet):
            """Viewset for State model."""

            queryset = models.State.objects.all()

            serializers = {
                "list": states.StateListSerializer,
                "retrieve": states.StateSerializer,
            }

            filter_backends = (
                filters.DjangoFilterBackend,
                rest_filters.SearchFilter,
                rest_filters.OrderingFilter,
            )

            filterset_fields = (
                "country",
            )

            search_fields = (
                "name",
                "state_code",
            )

            ordering_fields = (
                "id",
                "name",
                "state_code",
            )

            ordering = ("name",)

            def get_serializer_class(self):
                return self.serializers.get(self.action)