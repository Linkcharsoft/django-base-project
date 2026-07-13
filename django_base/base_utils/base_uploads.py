import uuid
from pathlib import Path

from django.utils.deconstruct import deconstructible


@deconstructible
class unique_upload_to:
    """Callable para ``upload_to`` que renombra el archivo a
    ``<subdir>/<uuid4>.<ext>`` preservando la extensión original.

    Implementado como clase ``@deconstructible`` para que sea serializable
    por el migration writer de Django.

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

    def __init__(self, subdir):
        self.subdir = subdir

    def __call__(self, instance, filename):
        ext = Path(filename).suffix.lower()
        return f"{self.subdir}/{uuid.uuid4().hex}{ext}"
