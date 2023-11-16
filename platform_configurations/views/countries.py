from rest_framework import filters as rest_filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from django.conf import settings

from platform_configurations import models
from platform_configurations.serializers import countries


if settings.INCLUDE_LOCATION:

    class CountryViewSet(ReadOnlyModelViewSet):
        """Viewset for Country model."""

        queryset = models.Country.objects.all()

        serializers = {
            "list": countries.CountryListSerializer,
            "retrieve": countries.CountrySerializer,
        }

        filter_backends =(
            rest_filters.SearchFilter,
            rest_filters.OrderingFilter,
        )

        search_fields = (
            "name",
            "iso3",
        )

        ordering_fields = (
            "id",
            "name",
            "iso3",
        )

        ordering = ("name",)

        def get_serializer_class(self):
            return self.serializers.get(self.action)