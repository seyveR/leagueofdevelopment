#!/bin/sh
# Run as root from systemd. Briefly pause writes for a coordinated DB/files backup.
set -eu
umask 077
cd /opt/league
target="/opt/league/backups/$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$target"
resume() { docker compose start api-be mobile-app >/dev/null; }
trap resume EXIT
docker compose stop api-be mobile-app >/dev/null
docker compose exec -T postgres pg_dump -U liga -d liga -Fc > "$target/database.dump"
docker run --rm -v liga-public_liga-files:/data:ro postgres:17.5-alpine tar -C /data -czf - . > "$target/files.tar.gz"
cd "$target"
sha256sum database.dump files.tar.gz > SHA256SUMS
# Retention is deliberately manual until an off-server destination is configured.
