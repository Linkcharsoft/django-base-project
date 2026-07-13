# Extending: Google OAuth (social login)

**Scope.** How to add Google as a social login provider via `django-allauth` + `dj-rest-auth`. The endpoint exposes `POST /api/auth/google/` that accepts a Google access/ID token from the frontend and returns the project's own JWT pair.
**Not covered.** Other providers (Facebook, GitHub, Apple). The pattern is identical — swap `google` for the provider key in the steps below.

The base used to ship a `GoogleLogin` view + `SOCIALACCOUNT_PROVIDERS` config + `GOOGLE_REDIRECT_URI` env var, but they were extracted because most projects derived from this base don't need social login, and the ones that do tend to want a specific provider configuration anyway.

---

## When you need it

- The product asks for "Sign in with Google" as an option alongside email/password.
- You need to bootstrap user accounts from a corporate Google Workspace.

If you only need Google calendar / drive / gmail API access for already-logged-in users, you don't need this — those are OAuth scopes the frontend negotiates separately.

## Prerequisite — Google Cloud Console

1. Create a project at https://console.cloud.google.com (or reuse an existing one).
2. **APIs & Services → Credentials → Create credentials → OAuth client ID** of type "Web application".
3. Add **Authorized redirect URIs** matching the frontend callback (e.g. `http://localhost:3000/auth/google/callback`, plus the prod equivalent).
4. Copy the resulting **Client ID** and **Client secret** — you'll paste them into Django admin in step 7.

---

## Step-by-step

### 1. Register the allauth social apps in `INSTALLED_APPS`

In `django_base/settings/django_settings.py`, inside `BASE_APPS`:

```python
"allauth.socialaccount",
"allauth.socialaccount.providers.google",
```

Place them right after `"allauth.account"`. The two are already enough for Google — no extra deps to install (allauth itself is already in the base).

### 2. Add the redirect URI env var

In `django_base/settings/environment_variables.py`:

```python
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI", default="")
```

In `.env.example`:

```bash
# <-------------- Google OAuth (allauth) -------------->
# CLIENT_ID / CLIENT_SECRET go in Django admin (SocialApp model),
# not here. This is only the callback the frontend uses.
GOOGLE_REDIRECT_URI='http://localhost:3000/auth/google/callback'
```

### 3. Configure the provider scopes

In `django_base/settings/custom_settings.py`, near the bottom:

```python
# <-------------- Google OAuth -------------->
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email", "openid"],
        "AUTH_PARAMS": {"access_type": "offline"},  # request refresh_token
    }
}
```

`access_type=offline` makes Google issue a refresh token alongside the access token — needed if you want to call Google APIs on behalf of the user later. Drop it if you only need identity.

### 4. Add the `GoogleLogin` view

In `auth_api/views.py`, add the imports at the top:

```python
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
```

And the view at the bottom of the file:

```python
class TemporalOAuth2Client(OAuth2Client):
    """Workaround for a dj-rest-auth signature mismatch — drop when dj-rest-auth releases the fix."""

    def __init__(self, request, *args, **kwargs):
        tmp_args = list(args)
        (tmp_args.pop() if tmp_args else None)
        super().__init__(request, *tmp_args, **kwargs)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.GOOGLE_REDIRECT_URI
    client_class = TemporalOAuth2Client
```

> The `TemporalOAuth2Client` workaround exists because `dj-rest-auth` passes one more positional arg than `OAuth2Client` accepts in current versions. When `dj-rest-auth` ships a release that fixes the signature, drop this class and use `OAuth2Client` directly. Track the upstream issue before deleting.

### 5. Wire the URL

In `auth_api/urls.py`, add the import:

```python
from auth_api.views import GoogleLogin, ...  # add GoogleLogin to the existing import
```

And the route inside `urlpatterns`:

```python
path("google/", GoogleLogin.as_view(), name="google_login"),
```

This exposes `POST /api/auth/google/`. (Earlier versions used `dj-rest-auth/google/` — pick whatever path the frontend expects.)

### 6. Migrate

```bash
just migrate
```

`socialaccount` ships with its own migrations (`SocialAccount`, `SocialApp`, `SocialToken`).

### 7. Register the credentials in admin

The Client ID / Secret are **not** env vars — they live in the DB via the `SocialApp` model. This lets you swap creds without redeploying.

1. Create a superuser if you don't have one (`just manage createsuperuser`).
2. Open `/admin/socialaccount/socialapp/add/`.
3. Set:
   - **Provider**: Google
   - **Name**: anything readable
   - **Client id**: from step 0 (Google Cloud Console)
   - **Secret key**: ditto
   - **Sites**: attach `example.com` (or create a Site matching your real domain — `/admin/sites/site/`).
4. Save.

### 8. Frontend contract

The frontend handles the OAuth dance with Google (popup or redirect, your choice — `@react-oauth/google` is the common React lib), gets an `access_token` or `id_token`, and POSTs it to:

```http
POST /api/auth/google/
Content-Type: application/json

{
  "access_token": "<google-issued-access-token>",
  "id_token":     "<optional-google-id-token>"
}
```

The response is the project's own JWT pair (same shape as `/api/auth/login/`):

```json
{
  "access_token": "<your-jwt>",
  "refresh_token": "<your-refresh>",
  "user": { ... }
}
```

If the email matches an existing user, the social account links to it. If not, a new user is created automatically with `is_register_complete=False` (so the frontend can route them to the "complete profile" flow).

---

## Validation

1. `docker compose up -d && just migrate`.
2. Open `/admin/socialaccount/socialapp/` — your Google app is listed and attached to a Site.
3. From the frontend (or `curl` with a real Google token):
   ```bash
   curl -X POST http://localhost:8000/api/auth/google/ \
     -H "Content-Type: application/json" \
     -d '{"access_token": "<real-google-token>"}'
   ```
   Should return 200 with the JWT pair.
4. Re-open `/admin/socialaccount/socialaccount/` — a row exists linking the Google `uid` to the Django user.

## Troubleshooting

- **`{"non_field_errors": ["Social application not found"]}`** — step 7 wasn't done, or the `SocialApp` isn't attached to the active `Site` (check `SITE_ID` in settings vs the Site you attached).
- **`{"non_field_errors": ["Incorrect value"]}`** — the `access_token` you sent isn't valid against the Client ID configured in admin (mismatch between frontend's Google Client ID and what's in `SocialApp`).
- **`redirect_uri_mismatch` from Google's side** — the `GOOGLE_REDIRECT_URI` in `.env` doesn't match what's whitelisted in Google Cloud Console step 0.
- **Schema validation warns about `GoogleLogin`** — `dj-rest-auth`'s `SocialLoginView` doesn't declare a serializer that drf-spectacular can introspect. Add `@extend_schema(request=YourSerializer, responses=YourResponseSerializer)` if you want the endpoint in Swagger UI.

## Production notes

- **Always HTTPS** in production — Google rejects non-HTTPS callbacks except for `http://localhost`.
- **Rotate Client Secret** if it ever leaks: rotate in Google Cloud Console → update the value in admin → no redeploy needed.
- **Refresh tokens are stored in `SocialToken`**: if you need to call Google APIs offline, query `SocialToken.objects.get(account__user=user, account__provider='google').token_secret`.
- **Don't trust `id_token` blindly**: allauth validates it against Google's JWKS for you. If you bypass allauth and parse the token yourself elsewhere, do the JWKS check too.
