# Extending: Global places (country / state / city pickers)

**Scope.** How to add `django-global-places` to the project for ISO country lists, subdivisions, and city data.
**Not covered.** Geolocation / IP-to-location lookups, custom address normalization.

The base used to ship a `GLOBAL_PLACES` config dict in `configurations.py`, but the underlying library (`django-global-places`) was removed in the Phase 2 dependency diet. Follow this guide to wire it back when a project actually needs structured location data.

---

## When you need it

- Forms that ask for country / state / city with normalized values (not free-text).
- Filtering or grouping users / orgs / products by region.
- Anything that benefits from ISO 3166 codes instead of "USA" vs "United States" vs "U.S." duplicates.

If you only need a country dropdown, `django-countries` is lighter. `django-global-places` is for the country + state + city tree.

---

## Step-by-step

### 1. Add the dependency

```bash
uv add django-global-places
docker compose build
```

### 2. Register the app

In `django_base/settings/custom_settings.py`, add to `THIRD_APPS`:

```python
THIRD_APPS = [
    "global_places",
]
```

### 3. Add the config dict

In `django_base/settings/configurations.py`:

```python
# <-------------- Global places settings -------------->
GLOBAL_PLACES = {
    "INCLUDE_LOCATION": False,          # True if you need city-level data (heavier)
    "LOCATION_SCOPE": "state",          # "country" | "state" | "city"
    "INCLUDE_EXPANDED_COUNTRY": False,  # True for full country metadata (region, subregion, …)
}
```

Tune the values to the project — `INCLUDE_LOCATION=True` pulls a much larger seed dataset.

### 4. Wire the URLs

In `django_base/urls.py`:

```python
urlpatterns = [
    ...
    path("api/places/", include("global_places.urls")),
]
```

### 5. Migrate and seed

```bash
just migrate
just manage loaddata countries  # check the lib README for the exact fixture names
```

The lib ships management commands to seed countries / states / cities — read its docs to pick what you need.

---

## Validation

1. `GET /api/places/countries/` → returns a paginated list with ISO codes.
2. The Django admin shows the `Country` / `State` / `City` models under `Global places`.

## Notes

- **Seed data is large**: cities alone can be ~150k rows. Don't seed what you won't use.
- **Migration order**: load fixtures *after* `migrate`, not before — the lib needs its own tables first.
- **Forking the lib**: if you need to extend a model (e.g. add `iso_code_3` to `Country`), prefer a separate app with a FK rather than monkey-patching the lib's models.
