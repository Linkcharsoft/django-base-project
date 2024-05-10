from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model


from users.serializers import UserSerializer


class UserViewSet(GenericViewSet, RetrieveModelMixin, UpdateModelMixin):
    permission_classes = [IsAuthenticated]
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if {self.lookup_field: self.kwargs[lookup_url_kwarg]}.get("pk") != "me":
            raise NotFound()
        return self.request.user