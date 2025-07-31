# from django.urls import path
from .views import (
    CustomerViewset,
    RegisterViewset,
    ProductViewset,
    OrderViewset,
    CartViewSet,
    CartItemViewset,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"customers", CustomerViewset, basename="customer")
router.register(r"register", RegisterViewset, basename="register")
router.register(r"products", ProductViewset, basename="product")
router.register(r"orders", OrderViewset, basename="order")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemViewset, basename="cartItem")


urlpatterns = router.urls


# urlpatterns = [
#     path("customers/", CustomerViewset.as_view(), name="customerlist"),
#     path("register/", RegisterViewset.as_view(), name="register"),
# ]
