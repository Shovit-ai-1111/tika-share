#!/bin/sh
set -e

mkdir -p "${DATA_DIR:-/data}/media"

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py ensure_admin

exec "$@"
