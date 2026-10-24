#!/bin/bash
# Root operator entrypoint. Called only after plan/deployment approval.
set -euo pipefail
umask 077
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
release_dir=$(realpath "${1:?Supply the reviewed release bundle directory}")
[[ $release_dir =~ ^/opt/pixshare/releases/[0-9]+$ ]] || exit 1
image=$(cat "$release_dir/api-image")
[[ $image =~ ^ghcr\.io/edtosoy/pixshare-api@sha256:[0-9a-f]{64}$ ]] || exit 1
exec 9>/run/pixshare-operation.lock
flock -n 9 || { echo 'Another PixShare operation is running.' >&2; exit 1; }
for private_file in compose.env api.env backup.env app_password postgres_password; do
    path="/etc/pixshare/$private_file"
    [[ -f $path && ! -L $path && $(stat -c '%a:%u' "$path") == 600:0 ]] || {
        echo 'Required root-owned 0600 configuration is missing.' >&2; exit 1;
    }
done
chown -R root:root "$release_dir"
chmod -R go-w "$release_dir"
export PIXSHARE_API_IMAGE="$image"
compose=(docker compose --env-file /etc/pixshare/compose.env -f "$release_dir/compose.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" pull api postgres caddy
"${compose[@]}" up -d --wait --wait-timeout 120 postgres
"${compose[@]}" run --rm --no-deps api /app/.venv/bin/alembic upgrade head
# A failed readiness check leaves traffic held for operator review. Never downgrade DB.
"${compose[@]}" up -d --wait --wait-timeout 120 api
"${compose[@]}" run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
"${compose[@]}" up -d caddy
curl --fail --silent --show-error --retry 8 --retry-delay 5 --retry-all-errors \
    https://api.pixshare.edtosoy.com/ready > /dev/null
if [[ -L /opt/pixshare/current ]]; then
    previous=$(readlink -f /opt/pixshare/current)
    if [[ $previous != "$release_dir" ]]; then ln -sfn "$previous" /opt/pixshare/previous; fi
fi
ln -sfn "$release_dir" /opt/pixshare/current
install -m 0644 "$release_dir/pixshare-backup.service" /etc/systemd/system/
install -m 0644 "$release_dir/pixshare-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now pixshare-backup.timer
echo 'API readiness confirmed. Complete live authentication/media and recovery checks.'
