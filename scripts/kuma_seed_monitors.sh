#!/bin/bash
# Adds one Uptime Kuma HTTP monitor per public DNS name in this stack, and
# publishes them to a status page (which is what Homepage's uptimekuma widget
# reads -- see docs/containers/homepage.md).
#
# Usage:
#   bash scripts/kuma_seed_monitors.sh              # create monitors + status page
#   DRY_RUN=1 bash scripts/kuma_seed_monitors.sh    # show what it would do
#   KUMA_STATUS_PAGE=0 bash scripts/kuma_seed_monitors.sh   # monitors only
#
# The password is prompted for interactively and exported only into the
# `docker exec` environment. It is never passed as an argument (which would be
# visible in `ps`), never written to disk, and never echoed to the terminal.
# If the Kuma account has 2FA enabled, also set KUMA_TOTP=<6-digit code>.
set -euo pipefail

CONTAINER="${KUMA_CONTAINER:-uptime-kuma}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null | grep -q running; then
  echo "ERROR: container '$CONTAINER' is not running." >&2
  exit 1
fi

: "${KUMA_USERNAME:=kparton}"

# Credential order: environment, then Infisical, then prompt -- the same order
# scripts/add_device_proxy_hosts.py uses. Kuma's password is NOT in Infisical
# today (unlike NPM_ADMIN_PASSWORD / ADGUARD_ADMIN_PASSWORD), so this normally
# falls through to the prompt. Store it as KUMA_ADMIN_PASSWORD to make this
# run unattended:
#   python3 scripts/infisical_client.py set KUMA_ADMIN_PASSWORD '<password>'
if [ -z "${KUMA_PASSWORD:-}" ]; then
  KUMA_PASSWORD="$(python3 "$REPO/scripts/infisical_client.py" get KUMA_ADMIN_PASSWORD 2>/dev/null || true)"
  [ -n "$KUMA_PASSWORD" ] && echo "Using KUMA_ADMIN_PASSWORD from Infisical."
fi
if [ -z "${KUMA_PASSWORD:-}" ]; then
  read -r -s -p "Uptime Kuma password for '$KUMA_USERNAME': " KUMA_PASSWORD
  echo
fi
[ -z "$KUMA_PASSWORD" ] && { echo "ERROR: no password given." >&2; exit 1; }

docker cp "$REPO/scripts/kuma_seed_monitors.js" "$CONTAINER:/tmp/kuma_seed_monitors.js" >/dev/null

# NODE_PATH is required: the script is dropped in /tmp, so Node's default
# resolution never walks up to /app/node_modules where socket.io-client lives.
docker exec \
  -e NODE_PATH=/app/node_modules \
  -e KUMA_USERNAME="$KUMA_USERNAME" \
  -e KUMA_PASSWORD="$KUMA_PASSWORD" \
  -e KUMA_TOTP="${KUMA_TOTP:-}" \
  -e KUMA_STATUS_PAGE="${KUMA_STATUS_PAGE:-1}" \
  -e KUMA_STATUS_SLUG="${KUMA_STATUS_SLUG:-default}" \
  -e DRY_RUN="${DRY_RUN:-0}" \
  "$CONTAINER" node /tmp/kuma_seed_monitors.js
rc=$?

docker exec "$CONTAINER" rm -f /tmp/kuma_seed_monitors.js >/dev/null 2>&1 || true
exit $rc
