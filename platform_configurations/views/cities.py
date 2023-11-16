from rest_framework.viewsets import ReadOnlyModelViewSet

from django.conf import settings

from platform_configurations import models
from platform_configurations.serializers import cities



if settings.INCLUDE_LOCATION and models.get_abstract_city_model():
        class CityViewSet(ReadOnlyModelViewSet):
            """Viewset for City model."""

            queryset = models.City.objects.all()
            serializer_class = cities.CitySerializer