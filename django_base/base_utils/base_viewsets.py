from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status

class BaseModelViewSet(viewsets.ModelViewSet):

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)