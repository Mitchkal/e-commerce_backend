from django.shortcuts import render
from django.conf import settings
import logging
import time
import requests
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
    CustomerSerializer,
    RegisterSerializer,
    ProductSerializer,
    OrderSerializer,
    CartSerializer,
    CartItemSerializer,
    ReviewSerializer,
    PaymentSerializer,
    OrderItemSerializer,
)

# from rest_framework import generics
from rest_framework import viewsets
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter
from django.db.models import Case, When, BooleanField, Value, IntegerField
from .permissions import IsStaffOrReadOnly
from .pagination import ProductPagination, OrderPagination
from .utility import initiate_payment
from django.core.cache import cache

from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.db import transaction


logger = logging.getLogger(__name__)
User = get_user_model()


class CustomerAdminViewset(viewsets.ModelViewSet):
    """
    Viewset for Admin customer management
    """

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]


class SignupViewset(CreateAPIView):
    """
    viewset for customer signup
    """

    serializer_class = RegisterSerializer
    queryset = Customer.objects.all()
    permission_classes = []

    def perform_create(self, serializer):
        """
        Handle customer signup
        """
        serializer.save()
        # validate serializer
        serializer.is_valid(raise_exception=True)

        user = serializer.instance
        user.set_password(serializer.validated_data["password"])
        user.save()
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


class CustomerProfileViewset(RetrieveUpdateAPIView):
    """
    allows authenticated users to view and update their profile
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


# class RegisterViewset(viewsets.ModelViewSet):
#     """
#     Viewset for customer registration
#     """

#     serializer_class = RegisterSerializer
#     queryset = Customer.objects.all()

#     def get_queryset(self):
#         """
#         avoid listing registered customers
#         """
#         if self.request.method == "GET":
#             return Customer.objects.none()
#         return super().get_queryset()

#     def create(self, request, *args, **kwargs):
#         """
#         Handles customer registration
#         """
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()
#         return Response(
#             {
#                 "message": "User created Succesfully",
#                 "user": {
#                     "id": user.id,
#                     "email": user.email,
#                     "first_name": user.first_name,
#                     "last_name": user.last_name,
#                 },
#             },
#             status=status.HTTP_201_CREATED,
#         )


# Create your views here.


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

        # key = "product_list"
        # cached_products = cache.get(key)
        # if cached_products is None:
        #     cached_products = (
        #         Product.objects.all()
        #         .order_by("-price")
        #         .annotate(
        #             annotated_is_in_stock=Case(
        #                 When(stock__gt=0, then=Value(True)),
        #                 default=Value(False),
        #                 output_field=BooleanField(),
        #             )
        #         )
        #     )
        #     # cache queryset for 15 minutes
        #     cache.set(key, cached_products, timeout=60 * 15)
        # return cached_products

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
        cart = Cart.objects.get(user=request.user)
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
    Viewset for the cart model
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

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve cart for authenticated user
        """
        cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        get current user's cart
        """
        cart = Cart.objects.get(customer=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemViewset(viewsets.ModelViewSet):
    """
    Viewset for CartItem model
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


class CheckoutView(APIView):
    """
    Viewset for checkout operations
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Handles checkout for an authenticated user
        """
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
        order = Order.objects.create(
            customer=cart.customer,
            cart=cart,
            shipping_address=request.data.get("shipping_address", ""),
            billing_address=request.data.get("billing_address", ""),
            # products=cart.products.all(),
            # total_price=sum(item.product.price * item.quantity for item in cart_items),
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
        serializer = OrderSerializer(order)

        # serializer = self.get_serializer(order)
        # serializer.is_valid(raise_exception=True)
        # serializer.save(customer=cart.customer, products=cart.products.all())

        # # Clear cart after order creation
        # cart.products.clear()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class OrderViewset(viewsets.ModelViewSet):
    """
    Viewset for order model
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
                {"detail": "Cannot ,mark unprocessed order as shipped"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = OrderStatus.SHIPPED
        order.save()
        return Response(
            {"detail": "Order marked as shipped succesfully"},
            status=status.HTTP_200_OK,
        )

    # @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    # def retry_payment(self, request, *args, **kwargs):
    #     """
    #     Allow user to retry failed payment for an order
    #     """


#

# def create(self, request, *args, **kwargs):
#     """
#     Create an order for authenticated user
#     """
#     user = request.user

#     cart = Cart.objects.filter(customer=user).first()

#     if not cart:
#         return Response(
#             {"message": "Cart not Found"},
#             status=status.HTTP_404_NOT_FOUND,
#         )
#     cart_items = cart.cart_items.all()
#     print(f"Cart Items: {cart_items}")
#     if not cart_items.exists():
#         return Response(
#             {"message": "Cart is empty, cannot create order"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     total = sum(item.product.price * item.quantity for item in cart_items)

#     order = Order.objects.create(
#         customer=cart.customer,
#         cart=cart,
#         shipping_address=request.data.get("shipping_address", ""),
#         billing_address=request.data.get("billing_address", ""),
#         total_price=total,
#         # products=cart.products.all(),
#         # total_price=sum(item.product.price * item.quantity for item in cart_items),
#     )
#     for cart_item in cart.cart_items.all():
#         OrderItem.objects.create(
#             order=order,
#             product=cart_item.product,
#             quantity=cart_item.quantity,
#             price=cart_item.product.price,
#         )
#     # clear cart
#     cart.cart_items.all().delete()
#     cart.products.clear()

#     serializer = self.get_serializer(order)
#     # serializer.is_valid(raise_exception=True)
#     # serializer.save(customer=cart.customer, products=cart.products.all())

#     # # Clear cart after order creation
#     # cart.products.clear()
#     return Response(
#         {
#             "message": "Order created",
#             "order": serializer.data,
#             "order_id": str(order.id),
#             "total": float(order.total_amount),
#             "payment_url": f"/api/pay/{order.id}/"
#         },
#         status=status.HTTP_201_CREATED,
#     )


class PayView(APIView):
    """
    View for payment processing
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        """
        Payment processing with Paystack
        """
        user = request.user
        try:
            order = Order.objects.get(id=order_id, customer=user)
        except Order.DoesNotExist:
            return Response(
                {"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
        amount_override = 3  # fixed amount for testing
        status_code, result = initiate_payment(order=order, amount=amount_override)
        return Response(result, status=status_code)


class OrderItemViewset(viewsets.ModelViewSet):
    """
    Viewset for orderItem model
    """

    queyset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]


class ReviewViewset(viewsets.ModelViewSet):
    """
    Viewset for Review model
    """

    # queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    # permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        Save a review with the authenticated user as author
        """
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


class PaymentViewset(viewsets.ModelViewSet):
    """
    Viewset for payment model
    """

    queryset = Payment.objects.all()
    serializer = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Create payment for an order
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=request.user.customer)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    # def retry(self, request, pk=None):
    #     """
    #     Retry payment for an order if failed
    #     """
