#!/bin/bash
# Verifies that each service's scheduled backups are recent and intact.
# Read-only: never deletes or modifies backup files. Outputs a JSON array to stdout.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOW=$(date +%s)

# service|glob-pattern|type(zip|tgz|dir)|stale_after_days
CHECKS=(
  "sonarr|$REPO_ROOT/sonarr/config/Backups/scheduled/*.zip|zip|9"
  "radarr|$REPO_ROOT/radarr/config/Backups/scheduled/*.zip|zip|9"
  "sonarr-4k|$REPO_ROOT/sonarr-4k/config/Backups/scheduled/*.zip|zip|9"
  "radarr-4k|$REPO_ROOT/radarr-4k/config/Backups/scheduled/*.zip|zip|9"
  "prowlarr|$REPO_ROOT/prowlarr/config/Backups/scheduled/*.zip|zip|9"
  "tautulli|$REPO_ROOT/tautulli/config/backups/tautulli.backup-*.zip|zip|2"
  "huntarr|$REPO_ROOT/huntarr/config/backups/scheduled_backup_*|dir|5"
  "lazylibrarian|$REPO_ROOT/lazylibrarian/config/*.tgz|tgz|14"
  "audiobookshelf|$REPO_ROOT/audiobookshelf/metadata/backups/*|dir|14"
  "qdrant|$REPO_ROOT/qdrant/snapshots/second_brain/*.snapshot|raw|2"
  "infisical|$REPO_ROOT/infisical/backups/*.sql.gz|raw|2"
)

first=true
echo -n "["

for entry in "${CHECKS[@]}"; do
  IFS='|' read -r service pattern type stale_days <<< "$entry"

  latest=""
  latest_mtime=0
  shopt -s nullglob
  for f in $pattern; do
    mtime=$(stat -f "%m" "$f" 2>/dev/null || echo 0)
    if [ "$mtime" -gt "$latest_mtime" ]; then
      latest_mtime=$mtime
      latest=$f
    fi
  done
  shopt -u nullglob

  if [ "$first" = true ]; then first=false; else echo -n ","; fi

  if [ -z "$latest" ]; then
    python3 -c "
import json
print(json.dumps({
  'service': '$service', 'file': None, 'ageDays': None, 'sizeBytes': None,
  'integrityOk': False, 'stale': True, 'staleThresholdDays': $stale_days,
  'status': 'missing'
}), end='')
"
    continue
  fi

  age_days=$(( (NOW - latest_mtime) / 86400 ))

  if [ "$type" = "dir" ]; then
    size_bytes=$(du -sk "$latest" 2>/dev/null | awk '{print $1*1024}')
    file_count=$(find "$latest" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "${file_count:-0}" -gt 0 ] && [ "${size_bytes:-0}" -gt 0 ]; then
      integrity="true"
    else
      integrity="false"
    fi
  else
    size_bytes=$(stat -f "%z" "$latest" 2>/dev/null || echo 0)
    if [ "$type" = "zip" ]; then
      if unzip -t "$latest" >/dev/null 2>&1; then integrity="true"; else integrity="false"; fi
    elif [ "$type" = "raw" ]; then
      # No generic tool to validate this format (e.g. Qdrant's own
      # snapshot format) — non-empty is the only check available.
      if [ "${size_bytes:-0}" -gt 0 ]; then integrity="true"; else integrity="false"; fi
    else
      if tar -tzf "$latest" >/dev/null 2>&1; then integrity="true"; else integrity="false"; fi
    fi
  fi

  stale="false"
  [ "$age_days" -gt "$stale_days" ] && stale="true"

  integrity_py="False"; [ "$integrity" = "true" ] && integrity_py="True"
  stale_py="False"; [ "$stale" = "true" ] && stale_py="True"

  python3 -c "
import json
print(json.dumps({
  'service': '$service',
  'file': '$latest'.replace('$REPO_ROOT/', ''),
  'ageDays': $age_days,
  'sizeBytes': ${size_bytes:-0},
  'integrityOk': $integrity_py,
  'stale': $stale_py,
  'staleThresholdDays': $stale_days,
  'status': 'ok' if ($integrity_py and not $stale_py) else 'fail'
}), end='')
"
done

echo -n "]"
