# from django.urls import path
from .views import CustomerViewset, RegisterViewset
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"customers", CustomerViewset, basename="customer")
router.register(r"register", RegisterViewset, basename="register")

urlpatterns = router.urls


# urlpatterns = [
#     path("customers/", CustomerViewset.as_view(), name="customerlist"),
#     path("register/", RegisterViewset.as_view(), name="register"),
# ]
