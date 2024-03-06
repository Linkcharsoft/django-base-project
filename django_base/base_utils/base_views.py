import secrets

from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed


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
