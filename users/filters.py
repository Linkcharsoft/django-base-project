import django_filters as filters
from django.contrib.auth import get_user_model


class UserFilter(filters.FilterSet):
    created_at = filters.DateFromToRangeFilter(field_name="created_at")
    is_active = filters.BooleanFilter(field_name="is_active", lookup_expr="exact")

    class Meta:
        model = get_user_model()
        fields = [
            "created_at",
            "is_active",
        ]
