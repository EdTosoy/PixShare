#!/bin/sh
# Compose file-backed secrets retain host ownership. Read the root-owned file
# before the official PostgreSQL entrypoint switches to the postgres UID.
set -eu
PG_APP_PASSWORD=$(cat /run/secrets/app_password)
export PG_APP_PASSWORD
exec /usr/local/bin/docker-entrypoint.sh "$@"
