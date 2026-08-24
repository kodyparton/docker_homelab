#!/bin/bash
# Read-only check: does each container's network-share bind mount actually
# resolve right now? Sonarr/Radarr/qBittorrent all bind-mount SMB shares
# (/Volumes/media/*, /Volumes/downloads) that are mounted on the macOS host
# and passed through OrbStack's VM. That passthrough occasionally drops the
# mount (ENOENT) until the container is restarted. This script only detects
# the condition; remediation (restart) is handled by the n8n workflow.
set -u

declare -a CHECKS=(
  "sonarr:/mnt/tv"
  "sonarr-4k:/mnt/tv-4k"
  "radarr:/mnt/movies"
  "radarr-4k:/mnt/movies-4k"
  "qbittorrent:/mnt/downloads"
)

items=()
for entry in "${CHECKS[@]}"; do
  container="${entry%%:*}"
  path="${entry##*:}"

  if ! docker inspect "$container" >/dev/null 2>&1; then
    status="container_missing"; ok="false"
  elif docker exec "$container" sh -c "test -d '$path' && ls '$path' >/dev/null 2>&1"; then
    status="ok"; ok="true"
  else
    status="mount_inaccessible"; ok="false"
  fi

  items+=("{\"container\":\"$container\",\"path\":\"$path\",\"ok\":$ok,\"status\":\"$status\"}")
done

IFS=,
echo "[${items[*]}]"
