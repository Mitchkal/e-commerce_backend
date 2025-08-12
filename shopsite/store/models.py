from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.translation import gettext_lazy as _
import uuid
from cloudinary.models import CloudinaryField
from decimal import Decimal


class CustomerManager(BaseUserManager):
    """
    Custom manager for customer model.
    """

    def create_user(self, email=None, password=None, **extra_fields):
        """
        Create and save user given email and password
        """
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        """
        Create and save superuser given email and password
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


# Create your models here.
class Customer(AbstractBaseUser, PermissionsMixin):
    """
    Extends default django user model to include additional fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone_number = PhoneNumberField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "date_of_birth",
        "phone_number",
    ]
    objects = CustomerManager()

    def __str__(self):
        return self.email


def product_directory_path(instance, filename):
    """
    Returns path to product image directory using UUID
    if the instance.id is not yet set
    """
    product_id = instance.id or uuid.uuid4
    return f"products/{product_id}/{filename}"


class Product(models.Model):
    """
    Product model
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=product_directory_path, blank=True, null=True)
    # image = CloudinaryField("image", blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.CharField(max_length=100, blank=True, null=True)
    # rating = models.DecimalField(
    #     max_digits=3, decimal_places=2, default=0.0, blank=True, null=True
    # )
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0, blank=True, null=True
    )
    is_featured = models.BooleanField(default=False)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal("0.00"), blank=True, null=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["-price"], name="product_price_idx"),
            models.Index(fields=["-stock"], name="product_stock_idx"),
        ]
        ordering = ["-price"]

    @property
    def is_in_stock(self):
        """
        Returns True if product is in stock else False
        """
        return self.stock > 0

    # @property
    # def average_rating(self):
    #     """Calculate average product rating from reviews"""
    #     avg = self.reviews.aggregate(models.Avg("rating")["rating__avg"])
    #     return round(avg or 0, 2) if avg else "No reviews yet"

    def __str__(self):
        return self.name


class Inventory(models.Model):
    """
    Record of stock added to products
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, related_name="inventory_logs", on_delete=models.CASCADE
    )
    quantity_added = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Add {self.quantity_added} to {self.product.name} on {self.added_at}"


class Cart(models.Model):
    """
    Cart model
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    products = models.ManyToManyField(Product, through="CartItem", blank=True)
    # total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cart {self.id} - {self.customer.email}"


class OrderStatus(models.TextChoices):
    """
    Enum for order status
    """

    PENDING = "PENDING", _("Pending")
    CREATED = "CREATED", _("Created")
    PROCESSING = "PROCESSING", _("Processing")
    SHIPPED = "SHIPPED", _("Shipped")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")
    REFUNDED = "REFUNDED", _("Refunded")


class Order(models.Model):
    """
    Order model
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="orders"
    )
    cart = models.ForeignKey(
        Cart, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    shipping_address = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.CharField(max_length=255, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["-order_date"], name="order_date_index"),
            models.Index(fields=["status"], name="order_status_index"),
        ]
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order {self.id} - {self.customer.email} - {self.status}"

    @property
    def total_price(self):
        """
        Returns the total price of the order by summing price
        * quantity for each related CartItem.
        """
        return sum(item.quantity * item.product.price for item in self.items.all())


class OrderItem(models.Model):
    """
    Model for order items
    """

    # cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f" {self.quantity} x {self.product.name}"


class CartItem(models.Model):
    """
    Model for cart items
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Cart Item {self.id} - {self.cart.id} - {self.product.name}"


class Review(models.Model):
    """
    Model for product Reviews
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """To avoid duplicate reviews"""

        unique_together = ("product", "customer")

    def __str__(self):
        return f"{self.customer}-{self.product.name} - ({self.rating})"


class PaymentStatus(models.TextChoices):
    """
    Enumeration for payment status
    """

    PENDING = "PENDING", _("PENDING")
    COMPLETED = "COMPLETED", _("COMPLETED")
    FAILED = "FAILED", _("FAILED")


class Payment(models.Model):
    """
    Model for payments
    """

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    payment_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments", null=True, blank=True
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, blank=True, null=True
    )
    reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=50, default=PaymentStatus.PENDING)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["-payment_date"], name="payment_date_idx"),
            models.Index(fields=["-amount"], name="payment_amount_idx"),
        ]
        ordering = ["-amount"]

    def __str__(self):
        return f"Payment {self.payment_uuid} - {self.order.id if self.order else 'N/A'} - {self.status}"

    @property
    def is_succesful(self):
        """
        Return True on succesful payment else False
        """
        return self.status == PaymentStatus.COMPLETED
