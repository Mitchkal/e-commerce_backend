from rest_framework import serializers
from .models import Customer, Product, Order, Cart, CartItem, Review
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken


user = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for customer model
    """

    class Meta:
        model = Customer
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "date_joined",
            "is_active",
            "is_staff",
        ]

    read_only_fields = ["id", "date_joined", "is_active", "is_staff"]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for customer registration
    """

    password = serializers.CharField(
        write_only=True, min_length=6, style={"input_type": "password"}
    )
    token = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "password",
            "token",
        ]

    def create(self, validated_data):
        """
        Create a new customer instance
        """
        user = Customer.objects.create_user(
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone_number=validated_data.get("phone_number", ""),
            date_of_birth=validated_data.get("date_of_birth", ""),
            password=validated_data.get("password", ""),
        )
        return user

    def get_token(self, obj: Customer) -> dict:
        """
        Generate JWT token for user
        """
        refresh = RefreshToken.for_user(obj)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the product model
    """

    is_in_stock = serializers.BooleanField(
        source="annotated_is_in_stock", read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image",
            "stock",
            "created_at",
            "updated_at",
            "category",
            "tags",
            "is_in_stock",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model
    """

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "product",
            "total_price",
            "status",
            "order_date",
            "status",
        ]

        read_only_fields = ["id", "order_date", "status"]
        extra_kwargs = {
            "customer": {"required": True},
            "products": {"required": True},
            "total_amount": {"required": True},
        }


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart model
    """

    class Meta:
        model = Cart
        fields = ["id", "customer", "created_at"]
        read_only_fields = ["id", "created_at"]


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for CartItem model
    """

    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "cart", "product", "quantity"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "cart": {"required": True},
            "product": {"required": True},
            "quantity": {"required": True},
            "id": {"read_only": True},
        }


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Review model
    """

    class Meta:
        model = Review
        fields = ["id", "product", "customer", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "product": {"required": True},
            "customer": {"required": True},
            "rating": {"required": True},
            "comment": {"required": False},
        }
