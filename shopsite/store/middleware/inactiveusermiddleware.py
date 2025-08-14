from rest_framework.response import Response
from rest_framework import status
from django.utils.deprecation import MiddlewareMixin

class InactiveUserMiddleware(MiddlewareMixin):
    """
    catches inactive users and handles gracefully
    """
    def process_request(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            return Response({
		 "detail": "Your account is inactive please check your email to confirm."
            }, status=status.HTTP_403_FORBIDDEN)
