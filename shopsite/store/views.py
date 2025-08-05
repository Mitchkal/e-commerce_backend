from django.shortcuts import render
from django.conf import settings
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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter
from django.db.models import Case, When, BooleanField, Value, IntegerField
from .permissions import IsStaffOrReadOnly
from .pagination import ProductPagination, OrderPagination


User = get_user_model()


class CustomerViewset(viewsets.ModelViewSet):
    """
    Viewset for Customer model
    """

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class RegisterViewset(viewsets.ModelViewSet):
    """
    Viewset for customer registration
    """

    serializer_class = RegisterSerializer
    queryset = Customer.objects.all()

    def get_queryset(self):
        """
        avoid listing registered customers
        """
        if self.request.method == "GET":
            return Customer.objects.none()
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        """
        Handles customer registration
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User created Succesfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


# Create your views here.
class ProductViewset(viewsets.ModelViewSet):
    """
    Viewset for Product Model
    """

    # queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    permission_classes = [IsStaffOrReadOnly]
    paginaton_class = ProductPagination

    def get_queryset(self):
        """
        queryset for product model
        """
        return Product.objects.order_by("-price").annotate(
            annotated_is_in_stock=Case(
                When(stock__gt=0, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

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
        cart, created = Cart.objects.get_or_create(customer=request.user)
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


class OrderViewset(viewsets.ModelViewSet):
    """
    Viewset for order model
    """

    queryset = Order.objects.all().order_by("-order_date")
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def create(self, request, *args, **kwargs):
        """
        Create an order for authenticated user
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
        for cart_item in cart.cart_items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
            )
        # clear cart

        cart.cart_items.all().delete()
        cart.products.clear()

        serializer = self.get_serializer(order)
        # serializer.is_valid(raise_exception=True)
        # serializer.save(customer=cart.customer, products=cart.products.all())

        # # Clear cart after order creation
        # cart.products.clear()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def initiate_payment(self, request, *args, **kwargs):
        """
        Payment processing with Paystack
        """

        order = self.get_object()
        # if order.status.filter(status="success").exists():
        if order.status == "success":
            return Response({"message": "Order already paid"}, status=400)

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
            return Response(
                {"message": "Payment initialization failed", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"message": "An error occured", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # if order.status

        # return Response(
        #     {"message": "Payment processing not implemented"},
        #     status=status.HTTP_501_NOT_IMPLEMENTED,
        # )

        def cancel_order(self, request, args, **kwargs):
            """
            Placeholder for order cancellation
            """
            return Response(
                {"message": "Order cancellation not implemented"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )


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
