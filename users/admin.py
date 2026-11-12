from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import render

from security.admin import SecurityUserAdminMixin
from security.sessions import open_session
from users.models import Profile, User


class UserProfileInline(admin.StackedInline):
    model = Profile


@admin.action(description="Generar JWT para el usuario seleccionado")
def generate_jwt(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Seleccioná exactamente un usuario para generar su JWT.",
            level=messages.ERROR,
        )
        return None
    user = queryset.first()
    _session, refresh = open_session(
        user, user_agent=f"Generated from the admin by {request.user.get_username()}"
    )
    return render(
        request,
        "admin/users/generate_jwt.html",
        {
            "target_user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
    )


@admin.register(User)
class CustomUserAdmin(SecurityUserAdminMixin, UserAdmin):
    inlines = [UserProfileInline, *SecurityUserAdminMixin.security_inlines]
    # Username, names and is_active live on the detail page and in the filters:
    # at 1280 px (with both sidebars) the list fits the account and its security columns only.
    list_display = ("id", "email", "is_staff", *SecurityUserAdminMixin.security_list_display)
    list_filter = UserAdmin.list_filter + SecurityUserAdminMixin.security_list_filter
    actions = [generate_jwt, *SecurityUserAdminMixin.security_actions]
