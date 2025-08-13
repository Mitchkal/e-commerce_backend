import requests
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .models import Payment, PaymentStatus, OrderStatus
from .emails.tasks import send_email_task
from drf_spectacular.utils import extend_schema, OpenApiResponse
import hmac
import hashlib
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView



class PaystackWebhookView(APIView):
    """
    Handles paystack webhook events for processing
    """

    @extend_schema(
        description="Handles webhook events for payment success or failure",
        request={
            'type': "object",
            "properties": {
                "event": {"type": "string", "enum": ["charge.success", "invoice.payment_failed"], "example": "charge.success"},
                "description": {"type": "string", "description": "Webhook event type"},
                "data": {
                    "type": "object",
                    "properties": {

                        "reference": {"type": "string", "description": "Transaction reference"},
                        "amount": {"type": "number", "description": "Transaction amount"},
                        "currency": {"type": "string", "description": "Transaction currency"},
                        "status": {"type": "string", "description": "Transaction status"},
                    },
                    "required": ["reference"]
                }
            },
            "required": ["event", "data"]
        },
        responses={
            200: OpenApiResponse(description="Webhook received successfully"),
            400: OpenApiResponse(description="Invalid webhook payload"),
            404: OpenApiResponse(description="Payment not found"),
            500: OpenApiResponse(description="Internal server error", examples={"application/json": {"error": "Failed to send email notification"}}),
        },
    )
    @csrf_exempt
    def post(self, request):
        """
        Processes webhook events for payment success or failuer
        """

        if request.method == "POST":
            signature = request.headers.get("X-Paystack-Signature")
            computed_signature = hmac.new(
                key=settings.PAYSTACK_SECRET_KEY.encode(),
                msg=request.body,
                digestmod=hashlib.sha512
            ).hexdigest()

            if not hmac.compare_digest(signature, computed_signature):
                return JsonResponse({"error": "Invalid signature"}, status=400)
            
            try:
                payload = json.loads(request.body)
                event = payload.get("event")
                data = payload.get("data", {})

                if event == "charge.success":
                    reference = data.get("reference")

                    if not reference:
                        return Response(
                            {"error": "Reference not found"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    headers = {
                            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
                        }
                    verify_url = (
                            f"https://api.paystack.co/transaction/verify/{reference}"
                        )
                    response = requests.get(verify_url, headers=headers)
                    result = response.json()
                    if ( result.get("status") and result.get("data", {}).get("status") == "success"):
                        try:
                            payment, created = Payment.objects.get_or_create(
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
                                        return Response(
                                            {
                                                "error": f"Failed to send email notification: {str(e)}"
                                            },
                                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                        )
                        except Payment.DoesNotExist:
                            return Response(
                                {"error": "Payment not found"}, 
                                status=status.HTTP_404_NOT_FOUND
                            )
                    else:
                        return Response(
                            {"error": "Payment verification failed"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )

                elif event == "invoice.payment_failed":
                    reference = data.get("reference")
                    if not reference:
                        return Response(
                            {"error": "Reference not found"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    try:
                        payment = Payment.objects.get(transaction_id=reference)
                        payment.status = PaymentStatus.FAILED
                        payment.save()
                    except Payment.DoesNotExist:
                        return Response({"error": "Payment not found"},
                                        status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response({"error": "Event not recognized"},
                                    status=status.HTTP_400_BAD_REQUEST)
                return Response(
                    {"message": "Webhook processed successfully"},
                    status=status.HTTP_200_OK
                )
            except json.JSONDecodeError:
                return Response({"error": "Invalid JSON payload"},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
