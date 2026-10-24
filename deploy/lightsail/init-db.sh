#!/bin/sh
# Runs only when the dedicated PostgreSQL volume is empty.
set -eu
# Loaded by the root wrapper before the official entrypoint drops privileges.
: "${PG_APP_PASSWORD:?Private application password was not injected}"
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-psqlrc --set ON_ERROR_STOP=1 <<'SQL'
\getenv app_password PG_APP_PASSWORD
CREATE ROLE pixshare LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
ALTER DATABASE pixshare OWNER TO pixshare;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO pixshare;
SQL
unset PG_APP_PASSWORD
