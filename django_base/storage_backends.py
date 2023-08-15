from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.storage import get_storage_class


class MediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = False


class StaticStorage(S3Boto3Storage):
    location = "static"
    default_acl = "public-read"


class PublicMediaStorage(S3Boto3Storage):
    location = "media"
    default_acl = "public-read"
    file_overwrite = False

    def get_object_parameters(self, args, **kwargs):
        params = super().get_object_parameters(args, **kwargs)
        
        if args.startswith("media/files"):
            params["ContentDisposition"] = "attachment"
        return params


class PrivateMediaStorage(S3Boto3Storage):
    location = "private"
    default_acl = "private"
    file_overwrite = False
    custom_domain = False


class CachedS3Boto3Storage(S3Boto3Storage):
    """
    S3 storage backend that saves the files locally, too.
    """

    default_acl = "public-read"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage"
        )()

    def save(self, name, content):
        self.local_storage._save(name, content)
        super().save(name, self.local_storage._open(name))
        return name
