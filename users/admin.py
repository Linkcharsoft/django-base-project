from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import Profile, User


class UserProfileInline(admin.StackedInline):
    model = Profile


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("is_test_user",)}),)
    list_display = ("id",) + UserAdmin.list_display + ("is_test_user",)


admin.site.register(User, CustomUserAdmin)
