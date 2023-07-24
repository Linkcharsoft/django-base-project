from django.contrib.admin.filters import SimpleListFilter
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import Profile, User


class SoftDeleteFilter(SimpleListFilter):
    title = "deleted"

    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("All", "All"),
            ("Yes", "Yes"),
            (None, "No"),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": cl.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.filter(deleted=True)
        if self.value() == "All":
            return queryset
        else:
            return queryset.filter(deleted=False)


class UserProfileInline(admin.StackedInline):
    model = Profile

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """
        Return a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model.unfiltered_objects.get_queryset()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    fieldsets = UserAdmin.fieldsets + ((("Custom Fields"), {"fields": ["deleted"]}),)
    list_filter = [
        SoftDeleteFilter,
    ] + list(UserAdmin.list_filter[:2])
    list_display = UserAdmin.list_display + ("deleted",)

    def get_queryset(self, request):
        """
        Return a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model.unfiltered_objects.get_queryset()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def delete_queryset(self, request, queryset):
        queryset.update(deleted=True)
        for user in queryset:
            user.profile.deleted = True
            user.profile.save()


admin.site.register(User, CustomUserAdmin)
