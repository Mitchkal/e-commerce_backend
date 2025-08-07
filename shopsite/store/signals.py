from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Order
from django.core.cache import cache


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
