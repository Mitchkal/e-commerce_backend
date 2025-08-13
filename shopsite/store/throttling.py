import logging
import os
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger("throttle_logger")

class CustomAnonRateThrottle(AnonRateThrottle):
    """
    Custom rate throttle for anonymous users.
    """

    scope = "custom_anon"

    def allow_request(self, request, view):
        """
        allow requests
        """
        self.request = request
        return super().allow_request(request, view)

    def throttle_failure(self):
        """
        Log throttle failure for anonymous user
        """
        # self.request = request
        ip = self.get_ident(self.request)
        logger.warning(f"Anonymous user throttled exceeded: IP={ip}")
        return super().throttle_failure()


class CustomUserRateThrottle(UserRateThrottle):
    """
    Custom rate throttle for authenticated users.
    """

    scope = "custom_user"

    def allow_request(self, request, view):
        """
        Allow requests for authenticated users
        """
        self.request = request
        return super().allow_request(request, view)

    def throttle_failure(self):
        """
        Log throttle failure for authenticated user
        """
        user = self.request.user
        user_id = user, id if user.is_authenticated else "Anonymous"
        logger.warning(
            f"Authenticated user throttled exceeded: user={user}  (ID={user_id})"
        )
        return super().throttle_failure()
