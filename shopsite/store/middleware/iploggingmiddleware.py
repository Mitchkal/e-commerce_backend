import logging
logger = logging.getLogger("ip_logger")
from ipware import get_client_ip

class IPLoggingMiddleware:
    def __init__(self, get_response):
        """
        middleware to log incoming ip requests
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Log ip address of incoming request
        """
        client_ip, is_routable = get_client_ip(request)
        if client_ip:
            logger.info(f"Incoming request from IP: {client_ip}, Routable: {is_routable} to path: {request.path}")
        else:
            logger.warning(f"Incoming request from unknown IP to path: {request.path}")
        response = self.get_response(request)
        return response
