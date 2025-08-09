import logging
import os
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

log_file_path = "store/throttling.log"
log_dir = os.path.dirname(log_file_path)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)
if not logger.handlers:
    try:
        handler = logging.FileHandler(log_file_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception as e:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.error(f"Error setting up logging: {e}, defaulting to console logging.")


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
