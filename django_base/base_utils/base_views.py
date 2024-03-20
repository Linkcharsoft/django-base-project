import os
import secrets
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseForbidden

from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature, b64_decode

from django_base.settings import MEDIA_ROOT


class TokenProtectedViewMixin:
    """
    Mixin to protect views with a token.
    """

    def perform_authentication(self, request):
        assert hasattr(self, "token"), (
            "You must define a `token` attribute in '%s'." % self.__class__.__name__
        )

        token = request.query_params.get("token", "")
        if not secrets.compare_digest(token, self.token):
            raise AuthenticationFailed()

        return super().perform_authentication(request)


class TokenProtectedAPIView(TokenProtectedViewMixin, APIView):
    """
    View to protect with a token.
    """

    pass


class SignedMediaView(APIView):
    def get(self, request, *args, **kwargs):
        signer = TimestampSigner()
        signature = request.query_params.get("signature")
        
        if signature is None:
            return HttpResponseBadRequest("Missing signature")

        try:
            path = signer.unsign(signature, max_age=3600)
            path = b64_decode(path.encode()).decode()

            if path != self.kwargs["path"]:
                raise BadSignature()

        except (SignatureExpired, BadSignature):
            return HttpResponseForbidden("Signature is not valid or has expired")

        file = open(MEDIA_ROOT / path, "rb")
        return FileResponse(file)
