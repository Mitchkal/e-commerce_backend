"""
Root URL configuration for shopsite project.
"""

from django.http import HttpResponse

from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def home(request):
    return HttpResponse("ShopSite API is up!", status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # API endpoints
    path("api/", include(("store.urls", "store"), namespace="store")),
    # Schema endpoints
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Home health check
    path("", home, name="home"),
]
# Static and media files for development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
