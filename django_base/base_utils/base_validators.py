import string

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


class NumberRequiredValidator:
    """
    Validate that the password contains at least one number.
    """

    def validate(self, password, user=None):
        if not any(char.isdigit() for char in password):
            raise ValidationError(self.get_help_text(), code="password_no_number")

    def get_help_text(self):
        return _("Password must contain at least one number.")


class SymbolValidator:
    """
    Validate that the password contains at least one ascii punctuation character.
    """

    def validate(self, password, user=None):
        if not any(char in password for char in string.punctuation):
            raise ValidationError(self.get_help_text(), code="password_no_symbol")

    def get_help_text(self):
        return _("Password must contain at least one symbol: %(simbol)s.") % {
            "simbol": string.punctuation
        }


class UpperValidator:
    """
    Validate that the password contains at least one uppercase character.
    """

    def validate(self, password, user=None):
        if not any(char.isupper() for char in password):
            raise ValidationError(self.get_help_text(), code="password_no_upper")

    def get_help_text(self):
        return _("Password must contain at least one uppercase letter.")


@deconstructible
class FileSizeValidator(object):
    def __init__(self, mb_limit=5):
        self.mb_limit = mb_limit

    def __call__(self, value):
        if value.size > self.mb_limit * 1024 * 1024:
            raise ValidationError(
                _("File too large. Size should not exceed %(file_limit)s MiB.")
                % {"file_limit": self.mb_limit}
            )
