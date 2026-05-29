"""drf-spectacular hooks that shape the public OpenAPI schema.

The base ships with `dj-rest-auth` + `allauth` mounted, which expose more
routes than the frontend actually uses. Rather than decorate dozens of
upstream views with `@extend_schema(exclude=True)`, the schema is filtered
in one place via a `PREPROCESSING_HOOKS` entry registered in
`SPECTACULAR_SETTINGS` (see `django_base/settings/custom_settings.py`).

When the frontend starts using a new dj-rest-auth route, add it to
`_PUBLIC_AUTH_PATHS` below. When you intentionally want an endpoint hidden,
prefer extending this filter — it keeps the policy auditable in one file
instead of scattering `exclude=True` decorators.
"""

from __future__ import annotations

# Auth endpoints the frontend actually consumes. Everything else under
# `/api/auth/...` is dropped from the schema (e.g. `auth/user/`,
# `auth/password/change/`, `auth/token/verify/` — mounted by dj-rest-auth
# but unused by the frontend, so they should not appear in the contract).
_PUBLIC_AUTH_PATHS = frozenset(
    {
        "/api/auth/login/",
        "/api/auth/logout/",
        "/api/auth/token/refresh/",
        "/api/auth/registration/",
        "/api/auth/registration/verify-email/",
        "/api/auth/registration/resend-email/",
        "/api/auth/password/recovery/",
        "/api/auth/password/recovery/check-token/",
        "/api/auth/password/recovery/confirm/",
    }
)


def filter_public_endpoints(endpoints, **_kwargs):
    """Drop endpoints the project does not intend to expose publicly.

    Spectacular calls this hook with a list of
    ``(path, path_regex, method, callback)`` tuples and uses whatever this
    function returns. Two rules:

    1. **No PUT.** The project disables PUT globally via
       ``NoPutViewSetMixin`` (it answers 405), but the verb still shows up
       in the auto-generated schema and would mislead consumers. Strip it
       everywhere.
    2. **Auth whitelist.** Inside ``/api/auth/...``, keep only the paths
       listed in ``_PUBLIC_AUTH_PATHS``. Drop the rest.
    """
    filtered = []
    for entry in endpoints:
        path, _path_regex, method, _callback = entry
        if method == "PUT":
            continue
        if path.startswith("/api/auth/") and path not in _PUBLIC_AUTH_PATHS:
            continue
        filtered.append(entry)
    return filtered
