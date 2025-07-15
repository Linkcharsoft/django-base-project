from rest_framework import permissions


class HasRegisterCompletePermission(permissions.BasePermission):
    """
    Custom permission to only allow users with 'is_register_complete' status to access certain views.
    """

    message = "You need to complete your registration to access this resource."

    def has_permission(self, request, view):
        # Check if the user is authenticated and has 'is_register_complete' status
        return (
            request.user.is_authenticated and request.user.profile.is_register_complete
        )
