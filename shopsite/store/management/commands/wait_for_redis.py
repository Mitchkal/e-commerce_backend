import time
import redis
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    """Django command to wait for Redis availability"""

    def handle(self, *args, **options):
        self.stdout.write("Waiting for Redis...")

        # Get Redis URL from settings or use default
        redis_url = getattr(settings, "REDIS_URL", "redis://redis:6379/0")

        while True:
            try:
                r = redis.from_url(redis_url)
                r.ping()
                break
            except redis.ConnectionError:
                self.stdout.write("Redis unavailable, waiting 1 second...")
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Redis available!"))
