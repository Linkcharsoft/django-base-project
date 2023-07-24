import string

from django.core.exceptions import ValidationError


class NumberRequiredValidator:
    """
    Validate that the password contains at least one number.
    """

    def validate(self, password, user=None):
        if not any(char.isdigit() for char in password):
            raise ValidationError(self.get_help_text(), code="password_no_number")

    def get_help_text(self):
        return "Password must contain at least one number."


class SymbolValidator:
    """
    Validate that the password contains at least one ascii punctuation character.
    """

    def validate(self, password, user=None):
        if not any(char in password for char in string.punctuation):
            raise ValidationError(self.get_help_text(), code="password_no_symbol")

    def get_help_text(self):
        return f"Password must contain at least one symbol: {string.punctuation}."


class UpperValidator:
    """
    Validate that the password contains at least one uppercase character.
    """

    def validate(self, password, user=None):
        if not any(char.isupper() for char in password):
            raise ValidationError(self.get_help_text(), code="password_no_upper")

    def get_help_text(self):
        return "Password must contain at least one uppercase letter."
