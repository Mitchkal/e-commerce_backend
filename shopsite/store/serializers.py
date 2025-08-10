from rest_framework import serializers, status
from .models import Customer, Product, Order, Cart, CartItem, Review, Payment, OrderItem
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


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
        write_only=True,
        min_length=6,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    confirm_password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={"input_type": "password"},
        validators=[validate_password],
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
            "confirm_password",
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

    def validate_password(self, value):
        """
        Validate password strength
        """
        user = Customer(
            email=self.initial_data.get("email"),
            first_name=self.initial_data.get("first_name"),
            last_name=self.initial_data.get("last_name"),
        )
        if value != self.initial_data.get("confirm_password"):
            raise ValidationError({"password": "Passwords do not match"})
        try:
            validate_password(password=value, user=user)
        except DjangoValidationError as e:
            raise ValidationError(e.messages)
        return value

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


class OrderItemSerializer(serializers.ModelSerializer):
    """
    serializer for orderitem model
    """

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product",
            "quantity",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            # "cart": {"required": True},
            "order": {"required": True},
            "product": {"required": True},
            "quantity": {"required": True},
        }


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model
    """

    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "cart",
            "items",
            "total_price",
            "shipping_address",
            "billing_address",
            # "products",
            # "total_price",
            "status",
            "order_date",
            "status",
        ]

        read_only_fields = ["id", "order_date", "status"]
        extra_kwargs = {
            "customer": {"required": True},
            #     "products": {"required": True},
            #     "total_amount": {"required": True},
        }

    def validate(self, attrs):
        """
        Validate to ensure user only has one pending order at a time
        """
        user = self.context["request"].user
        if Order.objects.filter(
            customer=user, status=Order.OrderStatus.PENDING
        ).exists():
            raise serializers.ValidationError(
                "You already have a pending order, Please complete it first."
            )
        return attrs

    def get_total_price(self, obj) -> float:
        """
        Calculate total price of order
        """
        return sum(item.product.price * item.quantity for item in obj.items.all())


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart model
    """

    class Meta:
        model = Cart
        fields = ["id", "customer", "created_at", "products"]
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


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payment model
    """

    class Meta:
        model = Payment
        fields = [
            "payment_uuid",
            "order",
            "amount",
            "status",
            "payment_date",
            "payment_method",
        ]
        read_only_fields = [
            "payment_uuid",
            "payment_date",
            "order",
            "status",
            "payment_method",
            "amount",
        ]
        extra_kwargs = {
            "order": {"required": True},
            "amount": {"required": True},
            "status": {"required": True},
            "payment_method": {"required": True},
            "payment_status": {"required": True},
        }

class CheckoutRequestSerializer(serializers.Serializer):
    """
    Serializer for incoming checkout request
    """
    # cart_id = serializers.UUIDField(required=True)
    # payment_method = serializers.ChoiceField(
    #     choices=["credit_card", "paypal", "mpesa"], required=True
    # )
    shipping_address = serializers.CharField(required=True)
    billing_address = serializers.CharField(required=True)

# class CheckoutResponseSerializer(serializers.Serializer):
#     """
#     serializer for checkout response
#     """
#     message = serializers.CharField()
#     order_id = serializers.UUIDField()

class PayRequestSerializer(serializers.Serializer):
    """
    serializer for initiating a payment request
    """
    order_id = serializers.IntegerField(required=False)

class PayResponseSerializer(serializers.Serializer):
    """
    serializer for Paystack payment Response
    """
    status = serializers.CharField()
    message = serializers.CharField()
    data = serializers.JSONField()