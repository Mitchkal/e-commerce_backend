import requests
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .models import Payment, PaymentStatus, OrderStatus
from .emails.tasks import send_email_task
from drf_spectacular.utils import extend_schema, OpenApiResponse


@extend_schema(
    request=OpenApiResponse(description="Paystack webhook payload"),
    responses={
        200: OpenApiResponse(description="Webhook received successfully"),
        400: OpenApiResponse(description="Invalid webhook payload"),
    },
)
@csrf_exempt
def paystack_webhook(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            event = payload.get("event")
            data = payload.get("data", {})

            if event == "charge.success":
                reference = data.get("reference")
                if reference:
                    headers = {
                        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
                    }
                    verify_url = (
                        f"https://api.paystack.co/transaction/verify/{reference}"
                    )
                    response = requests.get(verify_url, headers=headers)
                    result = response.json()
                    if (
                        result.get("status")
                        and result.get("data", {}).get("status") == "success"
                    ):
                        try:
                            payment = Payment.objects.get_or_create(
                                transaction_id=reference,
                                defaults={
                                    "amount": result["data"]["amount"] / 100,
                                    "currency": result["data"]["currency"],
                                },
                            )
                            if payment.status != "COMPLETED":
                                payment.status = PaymentStatus.COMPLETED
                                payment.save()
                                if payment.order:
                                    payment.order.status = OrderStatus.CREATED
                                    payment.order.save()
                                    try:
                                        # send email notfication
                                        send_email_task(
                                            subject="Payment Succesful",
                                            template_name="emails/payment_success.html",
                                            context={
                                                "order": payment.order,
                                                "amount": payment.amount,
                                            },
                                            to_email=payment.order.customer.email,
                                        )
                                    except Exception as e:
                                        return JsonResponse(
                                            {
                                                "error": f"Failed to send email notification: {str(e)}"
                                            },
                                            status=500,
                                        )
                        except Payment.DoesNotExist:
                            return JsonResponse(
                                {"error": "Payment not found"}, status=404
                            )
                    else:
                        return JsonResponse(
                            {"error": "Payment verification failed"}, status=400
                        )

                else:
                    return JsonResponse({"error": "Reference not found"}, status=400)
            elif event == "invoice.payment_failed":
                reference = data.get("reference")
                if reference:
                    try:
                        payment = Payment.objects.get(transaction_id=reference)
                        payment.status = PaymentStatus.FAILED
                        payment.save()
                    except Payment.DoesNotExist:
                        return JsonResponse({"error": "Payment not found"}, status=404)
            else:
                return JsonResponse({"error": "Event not recognized"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
