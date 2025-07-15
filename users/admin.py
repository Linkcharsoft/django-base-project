from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import Profile, User


class UserProfileInline(admin.StackedInline):
    model = Profile


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    fieldsets = UserAdmin.fieldsets  # add here custom fields if you need to
    list_display = ("id",) + UserAdmin.list_display


admin.site.register(User, CustomUserAdmin)
