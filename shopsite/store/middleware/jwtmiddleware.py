from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import JsonResponse

class JWTBlacklistMiddleware:
    """
    Rejects requests with blacklisted JWT tokens
    """
    PUBLIC_PATHS = ["/", "/docs/", "/docs/swagger/", "/schema/", "/redoc/", "/api/products/"]

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        """
        Reject requests with blacklisted tokens
        """
        if any(request.path.startswith(path) for path in self.PUBLIC_PATHS):
            return self.get_response(request)
        try:
            user, token = self.jwt_auth.authenticate(request)
            if token and (
                BlacklistedToken.objects.filter(token=token).exists()
                # or OutstandingToken.objects.filter(token=token).exists()
            ):
                
                return JsonResponse(
                    {"detail": "Token is blacklisted"}, status=401
                )
        except (InvalidToken, AuthenticationFailed) as e:
            return JsonResponse({"detail": str(e)}, status=401)
        except Exception:
            return JsonResponse({"detail": "Invalid or missing token"}, status=401)
        return self.get_response(request)
