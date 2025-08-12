from django.shortcuts import render
from django.conf import settings
import logging


# from rest_framework import generics
from rest_framework import viewsets
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, GenericAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter
from django.db.models import Case, When, BooleanField, Value, IntegerField
from .permissions import IsStaffOrReadOnly
from .pagination import ProductPagination, OrderPagination
from .utility import initiate_payment
from django.core.cache import cache
from .emails.tasks import send_email_task
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes

from django.utils.decorators import method_decorator
from django.utils.http import urlencode, urlsafe_base64_encode, urlsafe_base64_decode
from django.db import transaction
from rest_framework.authentication import SessionAuthentication
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse


from .models import (
    Customer,
    Product,
    Order,
    Cart,
    CartItem,
    Review,
    Payment,
    OrderItem,
    OrderStatus,
)
from .serializers import (
    CheckoutRequestSerializer,
    # ConfirmEmailSerializer,
    CustomerSerializer,
    ForgotPasswordSerializer,
    PayRequestSerializer,
    RegisterSerializer,
    ProductSerializer,
    OrderSerializer,
    CartSerializer,
    CartItemSerializer,
    ResetPasswordSerializer,
    ReviewSerializer,
    PaymentSerializer,
    OrderItemSerializer,
    PayResponseSerializer,
)


logger = logging.getLogger(__name__)
User = get_user_model()


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    temporariliy exempt csrf in dev mode
    """

    def enforce_csrf(self, request):
        """
        Override to disable csrf check
        """
        return


class CustomerAdminViewset(viewsets.ModelViewSet):
    """
    Viewset for Admin CRUD operations for
    customer management
    """

    queryset = Customer.objects.all().order_by("id")
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]


class SignupViewset(CreateAPIView):
    """
    Viewset for customer signup
    Customer signs up with email and password
    and receives a welcome email.
    user is provided with JWT token on succesful signup
    """

    serializer_class = RegisterSerializer
    queryset = Customer.objects.all()
    permission_classes = []

    def perform_create(self, serializer):
        """
        Handle customer signup
        """
        customer = serializer.save(is_active=False)
        user = customer

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        confirm_link = f"{settings.FRONTEND_URL}/api/confirm-email/{uid}/{token}/"

        try:
            send_email_task.delay(
                subject="Confirm your email",
                template_name="emails/confirm_email.html",
                context={"user": user.first_name, "confirm_link": confirm_link},
                to_email=user.email,
            )
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {str(e)}")

        print(confirm_link)
        return Response(
            {
                "message": "User created",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ConfirmEmailView(APIView):
    """
    confirms user email
    """

    # serializer_class = ConfirmEmailSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("uuidb64", str, "Base64 encoded user ID"),
            OpenApiParameter("token", str, "Email confirmation token"),
        ],
        responses={
            200: OpenApiResponse(description="Email confirmed successfully"),
            400: OpenApiResponse(description="Invalid token or user does not exist"),
        },
    )
    def get(self, request, uuidb64, token):

        # serializer = self.serializer_class(data=request.data)
        # serializer.is_valid(raise_exception=True)

        # uid = serializer.validated_data.get("uuidb64")
        # token = serializer.validated_data.get("token")

        try:
            uid = urlsafe_base64_decode(uuidb64).decode()
            user = Customer.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
            return Response(
                {"error": "Invalid token or user does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()
        return Response(
            {"message": "Email confirmed successfully, You can now log in"},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(GenericAPIView):
    """
    sends passord reset token to user email
    """

    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer().data)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = Customer.objects.get(email=email)

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        reset_link = f"{settings.FRONTEND_URL}/api/reset-password/{uid}/{token}"

        send_email_task.delay(
            subject="Password Reset",
            template_name="emails/password_reset.html",
            to_email=user.email,
            context={"reset_link": reset_link, "user": user.first_name},
        )
        print(reset_link)
        return Response({"message": "Password reset link sent."})


class ResetPasswordView(APIView):
    """
    Accepts token and new passord to allow
    users update their password
    """

    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request, uuid64, token):
        """
        Accepts token and new password
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uid = urlsafe_base64_decode(uuid64, token)
            user = Customer.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
            return Response(
                {"error": "Invalid token or user does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_password = serializer.validated_data.get("password")
        if not new_password:
            return Response(
                {"error": "Password required"}, status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password updated successfully"})


class CustomerProfileViewset(RetrieveUpdateAPIView):
    """
    Allows authenticated users to view and update their profile
    """

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        return authenticated user
        """
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """
        retrieve profile for authenticated user
        """
        user = request.user
        print(f"user is {user}")
        cache_key = f"customer_profile_{user.id}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        serializer = self.get_serializer(user)
        cache.set(cache_key, serializer.data, timeout=60 * 16)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        profile update for authenticated user
        """
        user = request.user
        response = super().update(request, *args, **kwargs)

        # Invalidates cache after update
        cache_key = f"customer_profile_{user.id}"
        cache.delete(cache_key)

        return response


class ProductViewset(viewsets.ModelViewSet):
    """
    Viewset for Product Model CRUD operations
    supports filtering, pagination, and caching
    of list and detail responses
    """

    # queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = ProductPagination

    def get_queryset(self):
        """
        Returns queryset for product model ordered by price in
        descending order with annotated bollean field for staock availability
        Cached for 15 minutes to enhance performance
        """

        return (
            Product.objects.all()
            .order_by("-price")
            .annotate(
                annotated_is_in_stock=Case(
                    When(stock__gt=0, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
        )

    def list(self, request, *args, **kwargs):
        """
        Returns paginated product list with caching
        based on query parameters. Cache stored for 15 minutes
        """
        query_string = urlencode(request.query_params.items())
        cache_key = f"product_list_response_{query_string or 'all'}"

        try:
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return Response(cached_response)
        except Exception as e:
            logger.error(f"Cache retrieval failed for key {cache_key}: {str(e)}")

        response = super().list(request, *args, **kwargs)

        # cache for 15 minutes
        try:
            cache.set(cache_key, response.data, timeout=60 * 15)
            logger.debug(f"Cache set for key: {cache_key}")
        except Exception as e:
            logger.error(f"Cache set failed for key {cache_key}: {str(e)}")
        return response

    def retrieve(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        cache_key = f"product_detail_response_{pk}"
        try:

            cached_data = cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f" Cache hit for key: {cache_key}")
                return Response(cached_data)
        except Exception as e:
            logger.error(f"Cache retrieval failed for key {cache_key}: {str(e)}")

        response = super().retrieve(request, *args, **kwargs)

        try:
            cache.set(cache_key, response.data, timeout=60 * 15)
            logger.debug(f"Cached response for key: {cache_key}")
        except Exception as e:
            logger.error(f"Cache set failed for key {cache_key}: {str(e)}")
        return response

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def add_to_cart(self, request, pk=None):
        """
        Adds a product to the cart
        """
        product = self.get_object()
        if product.stock <= 0:
            return Response(
                {"message": "Product is out of stock"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cart, created = Cart.objects.get_or_create(customer=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": 1}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        return Response(
            {
                "message": "Product added to cart",
                "cart_item": CartItemSerializer(cart_item).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], permission_classes=[IsAuthenticated])
    def remove_from_cart(self, request, pk=None):
        """
        Removes a product from the cart
        """
        product = self.get_object()
        cart = Cart.objects.get(customer=request.user)
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()
        if cart_item:
            cart_item.delete()
            return Response(
                {"message": "Product removed from cart"},
                status=status.HTTP_204_NO_CONTENT,
            )
        return Response(
            {"message": "Product not found in cart"},
            status=status.HTTP_404_NOT_FOUND,
        )


class CartViewSet(viewsets.ModelViewSet):
    """
    Viewset for the cart model, restricted to the current user
    Allows authenticated users to view and manage their cart
    """

    queryset = Cart.objects.none()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return cart for authenticated user
        """
        user = self.request.user
        return Cart.objects.filter(customer=user)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        get current user's cart
        """
        cart = get_object_or_404(Cart, customer=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemViewset(viewsets.ModelViewSet):
    """
    Viewset for crud operations on items in
    a customer's cart.
    """

    queryset = CartItem.objects.none()
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return cart Items for the authenticated user
        """
        user = self.request.user
        # customer = Customer.objects.get(user=user)

        cart = Cart.objects.filter(customer=user).first()
        if cart:
            return CartItem.objects.filter(cart=cart)
        return CartItem.objects.none()


@extend_schema(
    request=CheckoutRequestSerializer,
    responses={201: OrderSerializer, 400: dict, 404: dict},
)
class CheckoutView(GenericAPIView):
    """
    Viewset to handle checkout operations.
    Allows authenticated users to create an
    order from their cart, then clears the cart.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutRequestSerializer
    response_serializer_class = OrderSerializer

    @transaction.atomic
    def post(self, request):
        """
        Handles checkout for an authenticated user
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        user = request.user
        cart = Cart.objects.filter(customer=user).first()

        if not cart:
            return Response(
                {"message": "Cart not Found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        cart_items = cart.cart_items.all()
        print(f"Cart Items: {cart_items}")
        if not cart_items.exists():
            return Response(
                {"message": "Cart is empty, cannot create order"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing_pending_order = Order.objects.filter(
            customer=user, status=OrderStatus.PENDING
        ).first()

        if existing_pending_order:
            return Response(
                {
                    "message": "You already have a pending order please complete it first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = Order.objects.create(
            customer=cart.customer,
            cart=cart,
            shipping_address=validated_data.get("shipping_address", ""),
            billing_address=validated_data.get("billing_address", ""),
        )

        for item in cart_items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
            )
        # clear cart

        cart.cart_items.all().delete()
        cart.products.clear()
        res_serializer = OrderSerializer(order)

        return Response(
            res_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class OrderViewset(viewsets.ModelViewSet):
    """
    Viewset for order model with custom functions to
    manage orders and mark their status
    """

    queryset = Order.objects.all().order_by("-order_date")
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        """
        Return a users orders only and
        all orders if user is staff
        """
        if self.request.user.is_staff:
            return Order.objects.all().order_by("-order_date")

        return Order.objects.filter(customer=self.request.user).order_by("-order_date")

    def create(self, request, *args, **kwargs):
        """
        Disable order creation throgh this viewset
        """
        return Response(
            {"detail": "Order creation via this endpoint is not allowed."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def cancel(self, request, *args, **kwargs):
        """
        Allow user to cancel an order
        """
        order = self.get_object()
        if order.customer != request.user:
            return Response(
                {"detail": "Not your order"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status != OrderStatus.PENDING:
            return Response(
                {"detail": "Cannot cancel order that is not pending"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = OrderStatus.CANCELLED
        order.save()
        return Response(
            {"detail": "Order Cancelled Succesfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def mark_as_completed(self, request, *args, **kwargs):
        """
        admin only endpoint for marking order as completed
        """
        order = self.get_object()
        if order.status != OrderStatus.SHIPPED:
            return Response(
                {"detail": "Cannot mark unshipped order as completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = OrderStatus.COMPLETED
        order.save()
        return Response(
            {"detail": "Order marked as completed succesfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def mark_as_shipped(self, request, *args, **kwargs):
        """
        admin only endpoint to mark order as shipped
        """
        order = self.get_object()

        if order.status != OrderStatus.PROCESSING:
            return Response(
                {"detail": "Cannot mark unprocessed order as shipped"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = OrderStatus.SHIPPED
        order.save()
        return Response(
            {"detail": "Order marked as shipped succesfully"},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=PayRequestSerializer, responses={200: PayResponseSerializer, 404: dict}
)
class PayView(GenericAPIView):
    """
    Processes payments for orders using paystack
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PayRequestSerializer

    def post(self, request, order_id=None):
        """
        Payment processing with Paystack
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        # order_id = request.data.get("order_id")
        try:
            order = Order.objects.get(customer=user, status=OrderStatus.PENDING)
        except Order.DoesNotExist:
            return Response(
                {"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
        amount_override = 3  # fixed amount for testing
        status_code, result = initiate_payment(
            order=order, amount_override=amount_override
        )
        return Response(result, status=status_code)


class OrderItemViewset(viewsets.ModelViewSet):
    """
    Viewset for orderItem model to
    manage items in an order
    """

    serializer_class = OrderItemSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return OrderItem.objects.all().order_by("-id")


class ReviewViewset(viewsets.ModelViewSet):
    """
    Viewset for Review model allowing CRUD operations

    """

    # queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        Save a review with the authenticated user as author.
        Allow review creation only if a customer has a paid order.
        """
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionError("You must be logged in to leave a review")
        user_order = Order.objects.filter(
            customer=user, status=OrderStatus.COMPLETED
        ).first()
        if not user_order:
            raise PermissionError("You must have a completed order to leave a review")

        serializer.save(author=self.request.user)

    def get_queryset(self):
        """
        return reviews filtered by product
        """
        product_id = self.kwargs.get("product_id")

        if product_id:
            return Review.objects.filter(product_id=product_id)
        return Review.objects.all()

    def list(self, request, *args, **kwargs):
        """
        override to cache product reviews
        """
        product_id = self.kwargs.get("product_id")
        cache_key = f"product_reviews_{product_id}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=60 * 15)
        return response


class PaymentViewset(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for payment model, Limited to read only
    to allow List, and Retrieve actions only
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        returns payments
        """
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(customer=user)


# class PaymentViewset(viewsets.ModelViewSet):
#     """
#     Viewset for payment model
#     """

#     queryset = Payment.objects.all()
#     serializer_class = PaymentSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         """
#         returns payments
#         """
#         user = self.request.user
#         if user.is_staff:
#             return Payment.objects.all()
#         return Payment.objects.filter(customer=user.customer)

#     def create(self, request, *args, **kwargs):
#         """
#         Payment creation through this viewset is not allowed, handled on pay view instead
#         """
#         return Response(
#             {"detail": "Payment creation via this endpoint is not allowed."},
#             status=status.HTTP_405_METHOD_NOT_ALLOWED,
#         )

#     def update(self, request, *args, **kwargs):
#         """
#         Disable payment updates through this endpoint
#         """
#         return Response(
#             {"detail": "Payment updates via this endpoint disallowed"},
#             status=status.HTTP_405_METHOD_NOT_ALLOWED,
#         )

#     def partial_update(self, request, *args, **kwargs):
#         """
#         Disable payment partial updates through this endpoint
#         """
#         return Response(
#             {"detail": "Payment partial updates via this endpoint disallowed"},
#             status=status.HTTP_405_METHOD_NOT_ALLOWED,
#         )

#     def destroy(self, request, *args, **kwargs):
#         """
#         Disable payment deletion through this endpoint
#         """
#         return Response(
#             {"detail": "Payment deletion via this endpoint disallowed"},
#             status=status.HTTP_405_METHOD_NOT_ALLOWED,
#         )
