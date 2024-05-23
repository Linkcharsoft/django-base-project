import tempfile
import shutil
from django.test import TestCase, override_settings


MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class NoMediaTestCase(TestCase):
    """
    This class is for automatically creating a temporary media root folder.
    All the files uploaded during the tests will be destroyed after the tests.
    """

    pass

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()
