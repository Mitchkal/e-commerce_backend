from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


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
