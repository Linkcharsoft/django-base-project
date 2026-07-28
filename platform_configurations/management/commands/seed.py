from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.module_loading import module_has_submodule


class Command(BaseCommand):
    help = (
        "Populate the database with demo data for frontend/manual testing. "
        "Runs the seed() function of every first-party app that defines a seeds.py. "
        "Idempotent — re-running updates in place instead of duplicating."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed only runs with DEBUG=True. Refusing.")

        # INSTALLED_APPS order = seed order. An app whose data depends on another
        # app's must be declared after it in MY_APPS.
        with transaction.atomic():
            for app_config in self._apps_with_seeds():
                summary = import_module(f"{app_config.name}.seeds").seed()
                self.stdout.write(f"  {app_config.label}: {summary or 'ok'}")

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _apps_with_seeds(self):
        """First-party apps (living under BASE_DIR) that ship a seeds.py."""
        base_dir = str(settings.BASE_DIR)
        for app_config in apps.get_app_configs():
            if app_config.path.startswith(base_dir) and module_has_submodule(
                app_config.module, "seeds"
            ):
                yield app_config
