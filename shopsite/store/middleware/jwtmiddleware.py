from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTBlacklistMiddleware:
    """
    Rejects requests with blacklisted JWT tokens
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        """
        Reject requests with blacklisted tokens
        """
        try:
            user, token = self.jwt_auth.authenticate(request)
            if token and (
                BlacklistedToken.objects.filter(token=token).exists()
                # or OutstandingToken.objects.filter(token=token).exists()
            ):
                
                raise AuthenticationFailed("Token is blacklisted")
        except AuthenticationFailed:
            raise
        except Exception:
            pass
        return self.get_response(request)
