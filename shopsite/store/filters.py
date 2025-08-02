import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    """
    Filter for Product model
    """

    name = django_filters.CharFilter(lookup_expr="iexact")
    is_in_stock = django_filters.BooleanFilter(field_name="annotated_is_in_stock")

    class Meta:
        model = Product
        fields = {
            "price": ["lt", "gt", "exact"],
            "category": ["exact"],
            "tags": ["icontains", "exact", "iexact"],
            "description": ["icontains", "exact", "iexact"],
            "rating": ["lt", "gt", "exact"],
            "is_featured": ["exact"],
            "discount": ["lt", "gt", "exact"],
        }
