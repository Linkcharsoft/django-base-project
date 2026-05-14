import uuid
from pathlib import Path


def unique_upload_to(subdir):
    """Callable para ``upload_to`` que renombra el archivo a
    ``<subdir>/<uuid4>.<ext>`` preservando la extensión original.

    Combinar con ``FileSizeValidator`` y ``FileExtensionValidator``::

        from django.core.validators import FileExtensionValidator
        from django_base.base_utils.base_uploads import unique_upload_to
        from django_base.base_utils.base_validators import FileSizeValidator

        avatar = models.ImageField(
            upload_to=unique_upload_to("avatars"),
            validators=[FileSizeValidator(mb_limit=5),
                        FileExtensionValidator(["jpg", "jpeg", "png"])],
            blank=True,
        )
    """

    def _wrapper(instance, filename):
        ext = Path(filename).suffix.lower()
        return f"{subdir}/{uuid.uuid4().hex}{ext}"

    return _wrapper
