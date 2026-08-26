"""Render every transactional template with sample data, to a folder and/or a real inbox.

The templates are only ever exercised end-to-end by a real send, and mail clients are the part
of the stack tests cannot cover. This renders all of them off one fixture set so a layout change
can be eyeballed in Gmail/Outlook before it ships.

Projects built on this base should add their own mails to SAMPLES as they add them.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string

from django_base.base_utils.utils import (
    email_template_sender,
    get_default_for_email_template,
)

FRONT = settings.FRONT_URL

# One fixture per template: (key, subject, template, context). The values mimic real rows —
# accented names, realistic URLs — so the preview stresses the layout the way production does
# rather than flattering it.
SAMPLES: list[tuple[str, str, str, dict]] = [
    (
        "email_confirmation",
        f"Confirma tu e-mail en {settings.APP_NAME}",
        "account/email/email_confirmation_message.html",
        {
            "user": {"get_full_name": "Ana Pérez", "username": "ana"},
            "activate_url": f"{FRONT}/verificar-email?key=Mzg6MXRvT3F6OmhKTGJ4",
        },
    ),
    (
        "password_recovery",
        f"Recuperá tu contraseña en {settings.APP_NAME}",
        "registration/password_recovery_email.html",
        {
            "user": {"get_full_name": "Ana Pérez", "username": "ana"},
            "normalized_request_type": "cambio",
            "request_type": "cambiar",
            "password_recovery_token_type": settings.PASSWORD_RECOVERY_TOKEN_TYPE,
            "full_url": f"{FRONT}/cambiar-password?token=aB3xY9",
            "recovery_token": "483920",
        },
    ),
]


class Command(BaseCommand):
    help = "Render every transactional email with sample data — to files and/or a real inbox."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            help="Send the previews to this address using the configured mail backend.",
        )
        parser.add_argument(
            "--out",
            default="",
            help="Write the rendered HTML to this directory (skipped when empty).",
        )
        parser.add_argument(
            "--only",
            default="",
            help="Comma-separated sample keys to limit the run (default: all).",
        )
        parser.add_argument(
            "--from",
            dest="from_email",
            default="",
            help=(
                "Override the sender. Needed when DEFAULT_FROM_EMAIL is an identity the provider "
                "has not verified, which would reject the whole run."
            ),
        )

    def handle(self, *args, **options):
        samples = SAMPLES
        if options["only"]:
            wanted = {key.strip() for key in options["only"].split(",") if key.strip()}
            unknown = wanted - {key for key, *_ in SAMPLES}
            if unknown:
                raise CommandError(f"Unknown sample(s): {', '.join(sorted(unknown))}")
            samples = [sample for sample in SAMPLES if sample[0] in wanted]

        out_dir = Path(options["out"]) if options["out"] else None
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

        sent = 0
        failed = 0
        for key, subject, template, context in samples:
            if out_dir:
                # Render off the same defaults the sender injects, or the preview would miss the
                # banner and footer entirely.
                html = render_to_string(template, {**context, **get_default_for_email_template()})
                (out_dir / f"{key}.html").write_text(html, encoding="utf-8")

            if not options["to"]:
                self.stdout.write(self.style.SUCCESS(f"{key} -> {template}"))
                continue

            # One rejected address (an unverified sender, a bounce) must not cost us the rest of
            # the batch: the point of a preview run is to see every template land.
            try:
                kwargs = {}
                if options["from_email"]:
                    kwargs["from_email"] = options["from_email"]
                email_template_sender(
                    f"[preview] {subject}",
                    template,
                    dict(context),
                    options["to"],
                    **kwargs,
                )
            except Exception as exc:  # noqa: BLE001 -- a preview reports failures, never raises
                failed += 1
                self.stderr.write(self.style.ERROR(f"{key} -> FAILED: {exc}"))
            else:
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"{key} -> sent"))

        if out_dir:
            self.stdout.write(f"HTML written to {out_dir.resolve()}")
        if options["to"]:
            self.stdout.write(self.style.SUCCESS(f"Sent {sent} preview(s) to {options['to']}"))
            if failed:
                raise CommandError(f"{failed} preview(s) failed to send.")
