FROM python:3.14-slim-bookworm

ARG INSTALL_DEV=false

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /code

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg wget gettext libpq5 && \
    install -d /etc/apt/keyrings && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client-16 && \
    apt-get purge -y gnupg wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --frozen --no-install-project; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi

COPY . .

RUN chmod +x ./entrypoint.sh ./entrypoint-dev.sh
