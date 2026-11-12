"""Revocable sessions behind the JWTs, and the log of every login attempt.

Validity of a session is computed when it is checked, never stored: it is valid while
``revoked_at`` is null and ``now < min(last_used_at + SESSION_IDLE_TTL, created_at +
SESSION_MAX_TTL)``. ``expires_at`` below is derived from those same fields for display.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_base.base_utils.base_models import BaseModel


class AuthSessionQuerySet(models.QuerySet):
    def valid(self, now=None):
        now = now or timezone.now()
        return self.filter(
            revoked_at__isnull=True,
            last_used_at__gt=now - settings.SESSION_IDLE_TTL,
            created_at__gt=now - settings.SESSION_MAX_TTL,
        )

    def expired(self, now=None):
        now = now or timezone.now()
        return self.filter(revoked_at__isnull=True).filter(
            Q(last_used_at__lte=now - settings.SESSION_IDLE_TTL)
            | Q(created_at__lte=now - settings.SESSION_MAX_TTL)
        )

    def revoked(self):
        return self.filter(revoked_at__isnull=False)

    def revoke(self, reason):
        """Revoke the still-open sessions in the queryset. Returns how many were closed."""
        return self.filter(revoked_at__isnull=True).update(
            revoked_at=timezone.now(), revoked_reason=reason
        )


class AuthSession(BaseModel):
    """One login: the refresh token and every access token derived from it carry its id."""

    class RevokedReason(models.TextChoices):
        LOGOUT = "logout", _("Logout")
        LOGOUT_ALL = "logout_all", _("Logout from every device")
        CLOSED_BY_USER = "closed_by_user", _("Closed by the user from another session")
        PASSWORD_CHANGE = "password_change", _("Password changed")
        PASSWORD_RESET = "password_reset", _("Password reset")
        USER_DEACTIVATED = "user_deactivated", _("User deactivated")
        ADMIN = "admin", _("Closed by an admin")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_sessions"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default="")
    last_used_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(
        max_length=32, choices=RevokedReason.choices, blank=True, default=""
    )

    objects = AuthSessionQuerySet.as_manager()

    class Meta:
        ordering = ["-last_used_at"]
        verbose_name = _("session")
        verbose_name_plural = _("sessions")
        indexes = [models.Index(fields=["user", "revoked_at"])]

    def __str__(self):
        return f"{self.user} · {self.ip_address or '-'} · {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def expires_at(self):
        return min(
            self.last_used_at + settings.SESSION_IDLE_TTL,
            self.created_at + settings.SESSION_MAX_TTL,
        )

    def is_valid(self, now=None):
        return self.revoked_at is None and (now or timezone.now()) < self.expires_at

    @property
    def status(self):
        if self.revoked_at is not None:
            return "revoked"
        return "active" if self.is_valid() else "expired"


class LoginEvent(models.Model):
    """One login attempt, to the API or to the Django admin, successful or not."""

    class Reason(models.TextChoices):
        OK = "ok", _("OK")
        BAD_PASSWORD = "bad_password", _("Wrong password")
        UNKNOWN_EMAIL = "unknown_email", _("Unknown email")
        EMAIL_NOT_VERIFIED = "email_not_verified", _("Email not verified")
        INACTIVE = "inactive", _("Inactive user")
        THROTTLED = "throttled", _("Too many attempts")
        NOT_STAFF = "not_staff", _("Not staff")
        INVALID = "invalid", _("Invalid request")

    class Source(models.TextChoices):
        API = "api", _("API")
        ADMIN = "admin", _("Admin")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    email = models.CharField(max_length=254, blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="login_events",
    )
    reason = models.CharField(max_length=32, choices=Reason.choices)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.API)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("login attempt")
        verbose_name_plural = _("login attempts")
        # The two rate-limit counts: attempts per IP and per email inside the window.
        indexes = [
            models.Index(fields=["ip_address", "created_at"]),
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.email} {self.reason}"

    @property
    def success(self):
        return self.reason == self.Reason.OK


class SecuritySummary(LoginEvent):
    """No table: the "Summary" entry of the Security admin section (see security/admin.py)."""

    class Meta:
        proxy = True
        verbose_name = _("summary")
        verbose_name_plural = _("summary")
