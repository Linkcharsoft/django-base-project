from rest_framework import permissions


class HasRegisterCompletePermission(permissions.BasePermission):
    """
    Custom permission to only allow users with 'is_register_complete' status to access certain views.
    """

    message = "You need to complete your registration to access this resource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = getattr(request.user, "profile", None)
        return bool(profile and profile.is_register_complete)
