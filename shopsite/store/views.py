from django.shortcuts import render
from django.conf import settings
import logging
import time
import requests
from .models import Customer, Product, Order, Cart, CartItem, Review, Payment, OrderItem
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
        Return orders for authenticated user
        """
        user = self.request.user
        return Order.objects.filter(customer=user).order_by("-order_date")

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
        # if order.status.filter(status="success").exists():
        if order.status == "success":
            return Response({"message": "Order already paid"}, status=400)
        if Payment.objects.filter(
            order=order, status__in=["pending", "success"]
        ).exists():
            return Response(
                {
                    "message": " Payment is already in progress or completed for this order."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # amount = order.total_amount
        amount = 3  # fixed amount for testing
        if not amount:
            return Response(
                {"message": "Order total amount not set"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {
            "amount": amount * 100,
            "currency": "KES",
            "email": order.customer.email,
            "reference": f"order_{order.id}_{int(time.time())}",
            "channels": ["mobile_money", "bank", "card", "ussd"],
            "metadata": {
                "order_id": str(order.id),
                "customer_id": str(order.customer.id),
                "customer_name": f"{order.customer.first_name} {order.customer.last_name}",
                "customer_email": order.customer.email,
                "order_total": float(order.total_price),
                "cart_id": str(order.cart.id if order.cart else None),
                "custom_fields": [
                    {
                        "display_name": "Order ID",
                        "variable_name": "order_id",
                        "value": str(order.id),
                    },
                    {
                        "display_name": "Cart Items",
                        "variable_name": "cart_items",
                        "value": ", ".join(
                            [str(item.name) for item in order.cart.products.all()]
                            if order.cart
                            else "N/A"
                        ),
                    },
                ],
            },
        }
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        transaction_url = "https://api.paystack.co/transaction/initialize"
        # verify_url = "https://api.paystack.co/transaction/verify/"
        try:
            response = requests.post(transaction_url, json=data, headers=headers)
            # response.raise_for_status()
            if response.status_code != 200:
                return Response(
                    {
                        "message": "Payment initialization failed",
                        "paystack_error": response.json(),
                    },
                    status=response.status_code,
                )
            payment_data = response.json()
            if payment_data.get("status") is True:
                # create payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    reference=payment_data["data"]["reference"],
                    status="pending",
                )
                return Response(
                    {
                        "message": "Payment initiated succesfully",
                        "checkout_url": payment_data["data"]["authorization_url"],
                        "reference": payment_data["data"]["reference"],
                        "payment_id": str(payment.id),
                        "order_id": str(order.id),
                        "order_total": float(order.total_price),
                        "customer_email": order.customer.email,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "message": "Payment initialization failed",
                        "error": payment_data.get("message", "unknown error"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Payment initialization failed: {str(e)}")
            return Response(
                {"message": "Payment initialization failed", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"An error occurred during payment processing: {str(e)}")
            return Response(
                {"message": "An error occured", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # if order.status

        # return Response(
        #     {"message": "Payment processing not implemented"},
        #     status=status.HTTP_501_NOT_IMPLEMENTED,
        # )

        # def cancel_order(self, request, args, **kwargs):
        #     """
        #     Placeholder for order cancellation
        #     """
        #     return Response(
        #         {"message": "Order cancellation not implemented"},
        #         status=status.HTTP_501_NOT_IMPLEMENTED,
        #     )


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
