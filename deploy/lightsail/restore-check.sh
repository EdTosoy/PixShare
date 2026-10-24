#!/bin/bash
# Isolated restore only; never points pg_restore at the application container.
set -euo pipefail
umask 077
[[ $EUID == 0 ]] || exit 1
exec 9>/run/pixshare-operation.lock
flock -n 9 || { echo 'Another PixShare operation is running.' >&2; exit 1; }
PIXSHARE_BACKUP_DIR=$(realpath "${1:?Supply an existing backup run directory}")
export PIXSHARE_BACKUP_DIR
[[ $PIXSHARE_BACKUP_DIR == /var/backups/pixshare/* && -f $PIXSHARE_BACKUP_DIR/verified/database.dump ]] || exit 1
bundle=$(readlink -f /opt/pixshare/current)
compose=(docker compose --env-file /etc/pixshare/compose.env -f "$bundle/compose.yaml")
# Read only the public pinned PostgreSQL image through Compose's JSON output.
image=$("${compose[@]}" config --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["services"]["postgres"]["image"])')
[[ $image =~ ^postgres:17[^@]*@sha256:[0-9a-f]{64}$ ]] || exit 1
name="pixshare-restore-$(date +%s)-$RANDOM"
created=false
cleanup() { if $created; then docker rm -f "$name" > /dev/null; fi; }
trap cleanup EXIT
docker run -d --name "$name" --network none --memory 384m --cpus 0.5 --pids-limit 128 \
    --tmpfs /var/lib/postgresql/data:size=512m,mode=0700 \
    --mount type=bind,src=/etc/pixshare/postgres_password,dst=/run/secrets/postgres_password,readonly \
    -e POSTGRES_DB=pixshare -e POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password "$image" > /dev/null
created=true
ready=false
for _attempt in {1..60}; do
    if docker exec "$name" pg_isready -U postgres -d pixshare -q; then ready=true; break; fi
    sleep 1
done
$ready || exit 1
docker exec -i "$name" pg_restore -U postgres -d pixshare --exit-on-error --no-owner --no-acl < "$PIXSHARE_BACKUP_DIR/verified/database.dump"
docker exec -i "$name" psql -X -qAt -U postgres -d pixshare < "$bundle/rows.sql" > "$PIXSHARE_BACKUP_DIR/restored-rows.fingerprints"
cmp "$PIXSHARE_BACKUP_DIR/verified/rows.fingerprints" "$PIXSHARE_BACKUP_DIR/restored-rows.fingerprints"
echo 'Isolated PostgreSQL restore matches every users/posts row fingerprint.'
