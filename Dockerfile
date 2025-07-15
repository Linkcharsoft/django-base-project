FROM python:3.12.3

RUN apt update

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# We add this specific version of postgresql-client to avoid conflicts with the postgresql-client installed in the server
RUN apt-get install -y wget gnupg2 lsb-release && \
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

RUN apt-get update && \
    apt-get install -y cron gettext vim postgresql-client-15 htop

RUN pip install --upgrade pip && \
    pip install pip-tools

COPY requirements.txt ./
RUN pip-sync requirements.txt

COPY . .

RUN chmod +x ./entrypoint-dev.sh
RUN chmod +x ./entrypoint-dev.sh

# RUN mkdir -p /var/log/cron