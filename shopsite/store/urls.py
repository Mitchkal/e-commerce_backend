# from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConfirmEmailView,
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
    CheckoutView,
    PayView,
    PaymentViewset,
    ForgotPasswordView,
    ResetPasswordView,
    LogoutView,
)
from .webhook import PaystackWebhookView


router = DefaultRouter()
router.register(r"admin/customers", CustomerAdminViewset, basename="customer")
# router.register(r"register", RegisterViewset, basename="register")
router.register(r"products", ProductViewset, basename="product")
router.register(r"orders", OrderViewset, basename="order")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemViewset, basename="cartItem")
router.register(r"reviews", ReviewViewset, basename="review")
router.register(r"payment", PaymentViewset, basename="payment")


urlpatterns = [
    path("", include(router.urls)),
    path("webhook/paystack/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("signup/", SignupViewset.as_view(), name="signup"),
    path(
        "customer_profile/me/",
        CustomerProfileViewset.as_view(),
        name="customer-profile",
    ),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("pay/", PayView.as_view(), name="pay"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path(
        "reset-password/<str:uuid64>/<str:token>/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path(
        "api/confirm-email/<str:uuidb64>/<str:token>/",
        ConfirmEmailView.as_view(),
        name="confirm-email",
    ),
    path("logout/", LogoutView.as_view(), name="logout")
    # path(
    #     "reset-password/<uid>/<token>/",
    #     views.password_reset_form,
    #     name="password_reset_form",
    # ),
    # path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # path(
    #     "register/", RegisterViewset.as_view({"post", "create"}), name="register-create"
    # ),
]
# urlpatterns = router.urls
