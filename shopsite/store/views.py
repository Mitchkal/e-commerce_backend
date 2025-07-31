from django.shortcuts import render
from .models import Customer, Product, Order, Cart, CartItem
from .serializers import (
    CustomerSerializer,
    RegisterSerializer,
    ProductSerializer,
    OrderSerializer,
    CartSerializer,
    CartItemSerializer,
)

# from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.contrib.auth import get_user_model

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

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

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
        cart, created = Cart.objects.get_or_create(User, request.user)
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

    # queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return cart for authenticated user
        """
        user = self.request.user
        return Cart.objects.filter(customer__user=user)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve cart for authenticated user
        """
        cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewset(viewsets.ModelViewSet):
    """
    Viewset for CartItem model
    """

    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return cart Items for the authenticated user
        """
        user = self.request.user
        cart = Cart.objects.filter(customer__user=user).first()
        if cart:
            return CartItem.objects.filter(cart=cart)
        return CartItem.objects.none()


class OrderViewset(viewsets.ModelViewSet):
    """
    Viewset for order model
    """

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Create an order for authenticated user
        """
        user = request.user
        cart = Cart.objects.filter(customer__user=user).first()
        if not cart:
            return Response(
                {"message": "Cart not Found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not cart.products.exists():
            return Response(
                {"message": "Cart is empty, cannot create order"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=cart.customer, products=cart.products.all())

        # Clear cart after order creation
        cart.products.clear()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

        def make_payment(self, reuest, args, **kwargs):
            """
            placeholder for payment processing
            """
            return Response(
                {"message": "Payment processing not implemented"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        def cancel_order(self, request, args, **kwargs):
            """
            Placeholder for order cancellation
            """
            return Response(
                {"message": "Order cancellation not implemented"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
