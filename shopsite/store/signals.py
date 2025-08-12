from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import OrderItem, Product, Review, Order, OrderStatus, Inventory
from django.conf import settings
from django.core.cache import cache
from .emails.tasks import send_email_task
from django.db.models import Avg


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


# def update_product_stock(product, quantity):
#     """
#     Updates the stock product,
#     when a product is added to inventory
#     and when an order is placed


def update_product_average_rating(product):
    """
    Helper to recalculate and update a product's average rating
    """
    avg_rating = product.reviews.aggregate(avg=Avg("rating"))["avg"] or 0
    product.average_rating = Decimal(str(round(avg_rating, 2)))
    product.save(update_fields=["average_rating"])


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


@receiver(post_save, sender=Review)
def update_rating_on_save(sender, instance, **kwargs):
    """
    Update product average rating when review is saved
    """
    if instance.product is not None:
        update_product_average_rating(instance.product)


@receiver(post_delete, sender=Review)
def update_rating_on_delete(sender, instance, **kwargs):
    """
    Update product rating on review delete
    """
    if instance.product is not None:
        update_product_average_rating(instance.product)


@receiver(post_save, sender=Inventory)
def update_stock_on_iventory_add(sender, instance, created, **kwargs):
    """
    Update product stock when inventory is added
    """
    if created:
        product = instance.product
        if product:
            product.stock += instance.quantity_added
            product.save(update_fields=["stock"])
            cache.delete(f"product_detail_response_{product.id}")


@receiver(post_delete, sender=Inventory)
def update_stock_on_inventory_delete(sender, instance, **kwargs):
    """
    Update product stock if inventory record is deleted
    """
    product = instance.product
    if product:
        product.stock -= instance.quantity_added
        if product.stock < 0:
            product.stock = 0
        product.save(update_fields=["stock"])
        cache.delete(f"product_detail_response_{product.id}")


@receiver(post_save, sender=OrderItem)
def reduce_stock_on_order(sender, instance, created, **kwargs):
    """
    Reduce stock when order item is created
    """
    if created:
        product = instance.product
        if product:
            product.stock -= instance.quantity
            if product.stock < 0:
                product.stock = 0
            product.save(update_fields=["stock"])
            cache.delete(f"product_detail_response_{product.id}")


@receiver(post_delete, sender=OrderItem)
def restock_on_order_cancel(sender, instance, created, **kwargs):
    """
    Increase stock when order item is deleted
    such as cancelling
    or refunding
    """
    product = instance.product
    if product:
        product.stock += instance.quantity
        product.save(update_fields=["stock"])
        cache.delete(f"product_detail_response_{product.id}")
