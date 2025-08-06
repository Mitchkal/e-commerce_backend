# from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerAdminViewset,
    CustomerProfileViewset,
    SignupViewset,
    # CustomerViewset,
    # RegisterViewset,
    ProductViewset,
    OrderViewset,
    CartViewSet,
    CartItemViewset,
    ReviewViewset,
)
from .webhook import paystack_webhook


router = DefaultRouter()
router.register(r"customers", CustomerAdminViewset, basename="customer")
# router.register(r"register", RegisterViewset, basename="register")
router.register(r"products", ProductViewset, basename="product")
router.register(r"orders", OrderViewset, basename="order")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemViewset, basename="cartItem")
router.register(r"reviews", ReviewViewset, basename="review")


urlpatterns = [
    path("", include(router.urls)),
    path("webhook/paystack/", paystack_webhook, name="paystack-webhook"),
    path("signup/", SignupViewset.as_view(), name="signup"),
    path(
        "customers/me/",
        CustomerProfileViewset.as_view(),
        name="customer-profile",
    ),
    # path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # path(
    #     "register/", RegisterViewset.as_view({"post", "create"}), name="register-create"
    # ),
]
# urlpatterns = router.urls
