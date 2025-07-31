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
