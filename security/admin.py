"""The "Security" admin section: sessions, login attempts and a summary.

``SecurityUserAdminMixin`` adds the same figures to the User admin. It lives here instead of in
``users/admin.py`` so the whole feature travels with this folder.
"""

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from security.models import AuthSession, LoginEvent, SecuritySummary
from security.sessions import revoke_user_sessions
from security.stats import annotate_user_security, top_failing_ips, users_on_alert

RevokedReason = AuthSession.RevokedReason
USER_AGENT_PREVIEW = 16
# Compact timestamps (no year: records live 30-90 days) keep each list row on one line at 1280 px.
SHORT_DATETIME = "%b %d %H:%M"
STATUS_LABELS = {"active": _("Active"), "expired": _("Expired"), "revoked": _("Revoked")}


def _short(text, length=USER_AGENT_PREVIEW):
    return text if len(text) <= length else f"{text[:length]}…"


def _nowrap(value):
    return format_html('<span style="white-space:nowrap">{}</span>', value)


def _when(value):
    return _nowrap(timezone.localtime(value).strftime(SHORT_DATETIME)) if value else "-"


def _closed_message(count):
    return ngettext("%(count)d session closed.", "%(count)d sessions closed.", count) % {
        "count": count
    }


class SessionDisplayMixin:
    """List columns shared by the sessions list and the sessions inline of the User admin."""

    @admin.display(description=_("status"))
    def status_label(self, obj):
        """Status; when revoked, the reason shows on hover (and in the filter and detail page)."""
        if obj.status == "revoked":
            return format_html(
                '<span title="{}" style="text-decoration:underline dotted">{}</span>',
                obj.get_revoked_reason_display(),
                STATUS_LABELS["revoked"],
            )
        return STATUS_LABELS[obj.status]

    @admin.display(description=_("user agent"))
    def user_agent_short(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap">{}</span>',
            obj.user_agent,
            _short(obj.user_agent),
        )

    @admin.display(description=_("created"), ordering="created_at")
    def created(self, obj):
        return _when(obj.created_at)

    @admin.display(description=_("last used"), ordering="last_used_at")
    def last_used(self, obj):
        return _when(obj.last_used_at)

    @admin.display(description=_("expires"))
    def expires(self, obj):
        return _when(obj.expires_at)


# <---------------------- Sessions ---------------------->


class SessionStatusFilter(admin.SimpleListFilter):
    title = _("status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return list(STATUS_LABELS.items())

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "active":
            return queryset.valid(now)
        if self.value() == "expired":
            return queryset.expired(now)
        if self.value() == "revoked":
            return queryset.revoked()
        return queryset


@admin.register(AuthSession)
class AuthSessionAdmin(SessionDisplayMixin, admin.ModelAdmin):
    list_display = (
        "user",
        "status_label",
        "ip_address",
        "user_agent_short",
        "last_used",
        "expires",
    )
    list_filter = (SessionStatusFilter, "revoked_reason")
    search_fields = ("user__email", "ip_address")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "user",
        "status_label",
        "ip_address",
        "user_agent",
        "created_at",
        "last_used_at",
        "expires",
        "revoked_at",
        "revoked_reason",
    )
    fields = readonly_fields
    actions = ["close_sessions"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description=_("Close session"), permissions=["change"])
    def close_sessions(self, request, queryset):
        closed = queryset.revoke(RevokedReason.ADMIN)
        self.message_user(request, _closed_message(closed), messages.SUCCESS)


class AuthSessionInline(SessionDisplayMixin, admin.TabularInline):
    model = AuthSession
    extra = 0
    max_num = 0
    can_delete = False
    show_change_link = True
    fields = ("status_label", "ip_address", "user_agent_short", "created", "last_used", "expires")
    readonly_fields = fields
    ordering = ("-last_used_at",)

    def has_add_permission(self, request, obj=None):
        return False


# <---------------------- Login attempts ---------------------->


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("when", "email", "user", "reason", "source", "ip_address")
    list_filter = ("reason", "source", "created_at")
    search_fields = ("email", "ip_address")
    list_select_related = ("user",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description=_("when"), ordering="created_at")
    def when(self, obj):
        return _when(obj.created_at)


# <---------------------- Summary ---------------------->


@admin.register(SecuritySummary)
class SecuritySummaryAdmin(admin.ModelAdmin):
    """Not a list: the changelist renders users on alert and the IPs with the most failures."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            raise PermissionDenied
        user_model = get_user_model()
        valid_sessions = AuthSession.objects.valid()
        context = {
            **self.admin_site.each_context(request),
            **(extra_context or {}),
            "title": _("Security summary"),
            "opts": self.model._meta,
            "window_days": settings.SECURITY_FAILED_LOGINS_WINDOW.days,
            "alert_threshold": settings.SECURITY_FAILED_LOGINS_ALERT,
            "alert_users": users_on_alert(user_model.objects.all()),
            "top_ips": top_failing_ips(),
            "open_sessions": valid_sessions.count(),
            "users_with_sessions": valid_sessions.aggregate(n=Count("user", distinct=True))["n"],
            "user_changelist": (
                f"admin:{user_model._meta.app_label}_{user_model._meta.model_name}_changelist"
            ),
        }
        return TemplateResponse(request, "admin/security/summary.html", context)


# <---------------------- Users ---------------------->


class FailedLoginAlertFilter(admin.SimpleListFilter):
    title = _("security alert")
    parameter_name = "security_alert"

    def lookups(self, request, model_admin):
        return [("yes", _("On alert"))]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(failed_logins__gte=settings.SECURITY_FAILED_LOGINS_ALERT)
        return queryset


@admin.action(description=_("Close all sessions"), permissions=["change"])
def close_all_sessions(modeladmin, request, queryset):
    closed = sum(revoke_user_sessions(user, RevokedReason.ADMIN) for user in queryset)
    modeladmin.message_user(request, _closed_message(closed), messages.SUCCESS)


class SecurityUserAdminMixin:
    """Mix into the User ModelAdmin (before ``UserAdmin``) for sessions and failed logins."""

    security_list_display = ("active_sessions", "last_activity", "failed_logins")
    security_list_filter = (FailedLoginAlertFilter,)
    security_inlines = (AuthSessionInline,)
    security_actions = (close_all_sessions,)

    def get_queryset(self, request):
        return annotate_user_security(super().get_queryset(request))

    @admin.display(description=_("sessions"), ordering="active_sessions")
    def active_sessions(self, obj):
        return obj.active_sessions

    @admin.display(description=_("last used"), ordering="last_activity_at")
    def last_activity(self, obj):
        return _when(obj.last_activity_at)

    @admin.display(description=_("failed logins"), ordering="failed_logins")
    def failed_logins(self, obj):
        if obj.failed_logins >= settings.SECURITY_FAILED_LOGINS_ALERT:
            return format_html('<strong style="color:#ba2121">⚠ {}</strong>', obj.failed_logins)
        return obj.failed_logins
