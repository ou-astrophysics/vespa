# Vespa

The SuperWASP **V**ariabl**e** **S**tar **P**hotometry **A**rchive.

## Running Locally

You can run the latest build of the `main` branch in Docker with:

```
docker pull ghcr.io/ou-escape-eco/vespa
docker run -it --rm -p 8080:8080 ghcr.io/ou-escape-eco/vespa
```

This will run the Django dev server backed by a SQLite database.

You can also use docker-compose:

```
docker-compose build && docker-compose up
```

Or without Docker, install Pipenv in you Python environment and run:

```
pipenv install
./start_server.sh
```

## Data Import

There are three management commands for importing data:

* `python manage.py importclassifications class_top.csv` -- this must be run first. It will create database entries for all non-junk classifications.
* `python manage.py importlightcurves results_total.dat` -- this imports metadata about the period folding (skipping any records which don't already have database entries).
* `python manage.py importzooniverse superwasp-variable-stars-subjects.csv` -- this imports Zooniverse metadata (skipping any records which don't already have database entries).

## VPS Services

This is deployed on a VPS with Podman. Here are the initial commands used to set up the services:

```
podman pod create --name vespa -p 80:80

podman run -d --restart=always --pod=vespa --name vespa-postgres --label "io.containers.autoupdate=image" -v /opt/vespa/psql:/var/lib/postgresql/data:z --env-file /opt/vespa/postgres.env ghcr.io/ou-escape-eco/vespa-postgresql:latest

podman run -d --restart=always --pod=vespa --name vespa-rabbitmq --label "io.containers.autoupdate=image" -v /opt/vespa/rabbitmq/:/var/lib/rabbitmq/:z --env-file /opt/vespa/rabbitmq.env docker.io/rabbitmq:3

podman run -d --restart=always --pod=vespa --name vespa-nginx --label "io.containers.autoupdate=image" -v /opt/vespa/nginx.conf:/etc/nginx/nginx.conf:ro -v /opt/vespa/static/:/opt/vespa/static:z -v /srv/www/superwasp-live/media:/opt/vespa/media docker.io/nginx:1

podman run -d --restart=always --pod=vespa --name=vespa-django --label "io.containers.autoupdate=image"  --env-file /opt/vespa/prod.env -v /opt/vespa/static:/opt/vespa/static:z -v /srv/www/superwasp-live/astropy:/opt/vespa/astropy:z -v /srv/www/superwasp-live/media:/opt/vespa/media ghcr.io/ou-escape-eco/vespa

podman run -d --restart=always --pod=vespa --name=vespa-celery --label "io.containers.autoupdate=image"  --env-file /opt/vespa/prod.env -v /opt/vespa/static:/opt/vespa/static:z -v /srv/www/superwasp-live/astropy:/opt/vespa/astropy:z -v /srv/www/superwasp-live/media:/opt/vespa/media:z ghcr.io/ou-escape-eco/vespa bash ./start_worker.sh

cd /etc/systemd/system

podman generate systemd --new --name -f vespa

systemctl daemon-reload
systemctl enable pod-vespa.service
systemctl start pod-vespa.service
```