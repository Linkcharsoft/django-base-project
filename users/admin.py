from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken

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
    refresh = RefreshToken.for_user(user)
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
class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("is_test_user",)}),)
    list_display = ("id",) + UserAdmin.list_display + ("is_test_user",)
    actions = [generate_jwt]
