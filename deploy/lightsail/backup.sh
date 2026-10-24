#!/bin/bash
set -euo pipefail
umask 077
[[ $EUID == 0 ]] || exit 1
exec 9>/run/pixshare-operation.lock
flock -n 9 || { echo 'Another PixShare operation is running.' >&2; exit 1; }
bundle=$(readlink -f /opt/pixshare/current)
PIXSHARE_API_IMAGE=$(cat "$bundle/api-image")
BACKUP_ID=$(date -u +%Y%m%dT%H%M%SZ)
PIXSHARE_BACKUP_DIR=$(mktemp -d "/var/backups/pixshare/${BACKUP_ID}.XXXXXX")
export PIXSHARE_API_IMAGE BACKUP_ID PIXSHARE_BACKUP_DIR
compose=(docker compose --env-file /etc/pixshare/compose.env -f "$bundle/compose.yaml")
"${compose[@]}" ps --status running --services | grep -qx api
stopped=false
resume() {
    if $stopped; then "${compose[@]}" up -d --wait --wait-timeout 120 api; fi
}
trap resume EXIT
stopped=true
"${compose[@]}" stop api
"${compose[@]}" exec -T postgres pg_dump -U postgres -d pixshare --format=custom --no-owner --no-acl > "$PIXSHARE_BACKUP_DIR/database.dump"
"${compose[@]}" exec -T postgres psql -X -qAt -U postgres -d pixshare < "$bundle/rows.sql" > "$PIXSHARE_BACKUP_DIR/rows.fingerprints"
"${compose[@]}" run --rm --no-deps backup collect
resume
stopped=false
"${compose[@]}" run --rm --no-deps backup verify
"${compose[@]}" run --rm --no-deps -e BACKUP_ID backup upload
echo 'Backup complete. Run the isolated restoration drill before relying on it.'
# Retain failed runs and archives for review. Local pruning is manual and bounded
# to reviewed backup directories; offsite retention is governed by S3 lifecycle.
