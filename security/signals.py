"""Close a user's sessions when their password changes or they are deactivated.

Done on save so every path is covered (API, admin forms, toggle_block, shell). The view that
triggers the change can tune it before saving with ``mark_password_change``: the API password
change keeps the session making the request, the reset closes all of them with its own reason.
"""

from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from security.models import AuthSession
from security.sessions import revoke_user_sessions

RevokedReason = AuthSession.RevokedReason
_WATCHED_FIELDS = {"password", "is_active"}


def mark_password_change(user, reason=RevokedReason.PASSWORD_CHANGE, keep_session=None):
    """Call before saving a new password: which reason to record and which session survives."""
    user._session_revocation = (reason, keep_session)


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def remember_previous_credentials(sender, instance, update_fields=None, **kwargs):
    instance._previous_credentials = None
    if instance._state.adding or (update_fields and not _WATCHED_FIELDS & set(update_fields)):
        return
    instance._previous_credentials = (
        sender.objects.filter(pk=instance.pk).values_list("password", "is_active").first()
    )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def revoke_sessions_on_credential_change(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_credentials", None)
    if created or previous is None:
        return
    password, was_active = previous
    if was_active and not instance.is_active:
        revoke_user_sessions(instance, RevokedReason.USER_DEACTIVATED)
    elif password != instance.password:
        reason, keep = getattr(
            instance, "_session_revocation", (RevokedReason.PASSWORD_CHANGE, None)
        )
        revoke_user_sessions(instance, reason, keep=keep)
    instance._session_revocation = (RevokedReason.PASSWORD_CHANGE, None)
