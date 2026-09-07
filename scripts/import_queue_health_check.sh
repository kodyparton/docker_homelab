#!/bin/bash
# Read-only check: are completed downloads actually getting imported by
# Sonarr/Sonarr-4K/Radarr/Radarr-4K, or are they piling up stuck?
#
# Built 2026-08-28 after a real incident: /Volumes/downloads (the SMB share
# qBittorrent downloads into) presents every file as root-owned, mode 700,
# to the *arr containers -- regardless of who actually wrote it. Sonarr/Radarr
# run as PUID 1000 by default, which can't read root:700 files at all, so
# every completed download silently piled up in the "importPending" state
# forever. chmod from either the host or a container reports success but
# doesn't stick (the NAS enforces its own ACLs, not POSIX bits) -- the actual
# fix was switching Sonarr/Sonarr-4K/Radarr/Radarr-4K/Unpackerr to run as
# root (PUID/PGID 0), since root already has proven access to this mount.
#
# This script detects the SYMPTOM (items stuck in the import queue past a
# time threshold) rather than the specific permission cause, so it'll catch
# this class of problem even if a future regression has a different root
# cause. Remediation (deciding what to do about it) is a human/n8n decision;
# this script only reports.
set -u

STALE_MINUTES="${STALE_MINUTES:-60}"

declare -a APPS=(
  "sonarr:30027:SONARR_API_KEY"
  "sonarr-4k:30030:SONARR_4K_API_KEY"
  "radarr:30025:RADARR_API_KEY"
  "radarr-4k:30031:RADARR_4K_API_KEY"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

items=()
for entry in "${APPS[@]}"; do
  app="${entry%%:*}"
  rest="${entry#*:}"
  port="${rest%%:*}"
  keyname="${rest##*:}"

  api_key="$(python3 "$SCRIPT_DIR/infisical_client.py" get "$keyname" 2>/dev/null)"
  if [ -z "$api_key" ]; then
    items+=("{\"app\":\"$app\",\"ok\":false,\"status\":\"no_api_key\"}")
    continue
  fi

  queue_json="$(curl -s --max-time 15 "http://localhost:$port/api/v3/queue?pageSize=250" -H "X-Api-Key: $api_key")"
  if [ -z "$queue_json" ]; then
    items+=("{\"app\":\"$app\",\"ok\":false,\"status\":\"unreachable\"}")
    continue
  fi

  result="$(echo "$queue_json" | STALE_MINUTES="$STALE_MINUTES" python3 -c "
import sys, json, os
from datetime import datetime, timezone

stale_minutes = int(os.environ.get('STALE_MINUTES', '60'))
try:
    d = json.load(sys.stdin)
except Exception:
    print(json.dumps({'ok': False, 'status': 'bad_response'}))
    sys.exit()

now = datetime.now(timezone.utc)
stuck = []
for r in d.get('records', []):
    state = r.get('trackedDownloadState')
    if state not in ('importPending', 'importing'):
        continue
    added = r.get('added')
    if not added:
        continue
    try:
        added_dt = datetime.fromisoformat(added.replace('Z', '+00:00'))
    except ValueError:
        continue
    age_min = (now - added_dt).total_seconds() / 60
    if age_min >= stale_minutes:
        stuck.append({'title': r.get('title'), 'age_minutes': round(age_min)})

print(json.dumps({
    'ok': len(stuck) == 0,
    'status': 'ok' if not stuck else 'imports_stalled',
    'stuck_count': len(stuck),
    'oldest_stuck': max((s['age_minutes'] for s in stuck), default=0),
    'examples': stuck[:3],
}))
")"
  items+=("{\"app\":\"$app\",$(echo "$result" | sed 's/^{//;s/}$//')}")
done

IFS=,
echo "[${items[*]}]"
