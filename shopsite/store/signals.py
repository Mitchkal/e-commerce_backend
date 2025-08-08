from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Review, Order, OrderStatus
from django.conf import settings
from django.core.cache import cache
from .emails.tasks import send_email_task


@receiver([post_save, post_delete], sender=Product)
def clear_product_cache(sender, instance, **kwargs):
    """
    clears product_list cache when
    product is saved or deleted
    """
    try:
        # clear product list cache
        cache.delete_pattern("product_list_response_*")
        # clear product detail cache
        cache.delete(f"product_detail_response_{instance.id}")
    except Exception as e:
        print(f"Error clearing product cache: {e}")

    # cache_key = "product_list"
    # cache.delete(cache_key)


@receiver(
    [
        post_save,
    ],
    sender=Review,
)
def clear_review_cache(sender, instance, **kwargs):
    """
    Clear product review cache when a review is created or updated.
    """
    if instance.product is not None:
        product_id = instance.product.id
        cache_key = f"product_reviews_{product_id}"
        cache.delete(cache_key)


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """
    sends email to user when order status changes to shipped
    """
    if not created and instance.status == OrderStatus.SHIPPED:
        try:
            send_email_task(
                subject="Order Shipped",
                template_name="emails/order_shipped.html",
                context={
                    "order": instance,
                    "customer": instance.customer,
                },
                to_email=instance.customer.email,
            )
        except Exception as e:
            print(f"Error sending order shipped email: {e}")
