import requests
import time
import logging
from django.conf import settings

from .models import Payment
from .models import PaymentStatus, OrderStatus

logger = logging.getLogger(__name__)


def initiate_payment(order, amount_override=None):
    """
    Handles core payment logic that initializes a paystack transaction
    Returns payment details or error response

    """
    # if order.status.filter(status="success").exists():
    if order.status == OrderStatus.CREATED:
        return 400, {"message": "Order already paid"}

    if Payment.objects.filter(
        order=order, status__in=["completed", "processing", "shipped"]
    ).exists():
        return 400, {
            "message": " Payment is already in progress or completed for this order."
        }

    # amount = order.total_amount
    amount = amount_override if amount_override else order.total_price
    if not amount or amount <= 0:
        logger.error(f"Invalid order amount: {amount} for order {order.id}")
        return 400, {"message": "Invalid order amount"}
    if not amount:
        return (
            400,
            {"message": "Order total amount not set"},
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
            return response.status_code, {
                "message": "Payment initialization failed",
                "paystack_error": response.json(),
            }

        payment_data = response.json()
        if payment_data.get("status") is True:
            # create payment record
            payment = Payment.objects.create(
                order=order,
                customer=order.customer,
                amount=amount,
                reference=payment_data.get("data", {}).get("reference"),
                status=PaymentStatus.PENDING,
                payment_method="paystack",
            )
            return (
                200,
                {
                    "message": "Payment initiated succesfully",
                    "checkout_url": payment_data["data"]["authorization_url"],
                    "reference": payment_data["data"]["reference"],
                    "payment_id": str(payment.id),
                    "order_id": str(order.id),
                    "order_total": float(order.total_price),
                    "customer_email": order.customer.email,
                },
            )

        else:
            return (
                400,
                {
                    "message": "Payment initialization failed",
                    "error": payment_data.get("message", "unknown error"),
                },
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Payment initialization failed: {str(e)}")
        return (
            400,
            {"message": "Payment initialization failed", "error": str(e)},
        )
    except Exception as e:
        logger.error(f"An error occurred during payment processing: {str(e)}")
        return (
            500,
            {"message": "An error occured", "error": str(e)},
        )
