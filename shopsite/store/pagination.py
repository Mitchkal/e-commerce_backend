from rest_framework import pagination


class ProductPagination(pagination.PageNumberPagination):
    """
    Custom pagination class for product listing
    """

    page_size = 10  # Number of products per page
    page_size_query_param = "page_size"  # Client specified page size
    max_page_size = 100


class OrderPagination(pagination.PageNumberPagination):
    """
    Pagination for orders
    """

    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20
