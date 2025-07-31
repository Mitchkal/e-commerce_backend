from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.translation import gettext_lazy as _


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
    Returns path to product image directory
    """
    return f"products/{instance.id}/{filename}"


class Product(models.Model):
    """
    product model
    """

    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeFieldd(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_in_stock = models.BooleanField(default=True)
    image = models.ImageField(upload_to=product_directory_path, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.CharField(max_length=100, blank=True, null=True)
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.0, blank=True, null=True
    )
    discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0, blank=True, null=True
    )
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name


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

    id = models.UUIDFIeld(primary_key=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, deimal_places=2, default=0.0)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    shipping_address = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.CharField(max_length=255, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.customer.email} - {self.status}"


class Cart(models.Model):
    """
    Cart modeel
    """

    id = models.UUIDField(primary_key=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    products = models.ManyToManyField(Product, through="CartItem")

    def __str__(self):
        return f"Cart {self.id} - {self.customer.email}"


class CartItem(models.Model):
    """
    Model for cart items
    """

    id = models.UUIDField(primary_key=True, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Cart Item {self.id} - {self.cart.id} - {self.product.name}"
