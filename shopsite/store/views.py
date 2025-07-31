from django.shortcuts import render
from .models import Customer
from .serializers import CustomerSerializer, RegisterSerializer

# from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


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
