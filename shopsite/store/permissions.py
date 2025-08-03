from rest_framework.permissions import BasePermission


class IsStaffOrReadOnly(BasePermission):
    """
    Custom permission to allow only staff members
    to eddit objects with read access for others.
    """

    def has_permission(self, request, view):
        """
        Allow read-only access for non_authenticated users
        and full access for staff
        """
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff
