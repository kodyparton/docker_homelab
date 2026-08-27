#!/bin/bash
# Recurring disk housekeeping for the Mac Mini boot volume.
#
# Exists because the boot disk hit 95% full (12GB free) on 2026-08-26 and
# the single biggest consumer was Plex's PhotoTranscoder thumbnail cache at
# 34GB. That cache is regenerable and grows back, so trimming it needs to be
# scheduled rather than rediscovered manually at 95%.
#
# Safe by design: only ever removes regenerable cache files, never library
# data, never databases, never backups. Read-only elsewhere.
#
# Usage:
#   bash scripts/disk_maintenance.sh          # report only, changes nothing
#   bash scripts/disk_maintenance.sh --apply  # actually trim
set -uo pipefail

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

PLEX_CACHE="$HOME/Library/Application Support/Plex Media Server/Cache/PhotoTranscoder"
# Only trim the Plex cache once it exceeds this, so it stays useful day to day.
PLEX_TRIM_THRESHOLD_GB=10

human () { du -sh "$1" 2>/dev/null | awk '{print $1}'; }
gb_of  () { du -sk "$1" 2>/dev/null | awk '{printf "%.0f", $1/1048576}'; }

echo "=== Disk maintenance $(date '+%Y-%m-%d %H:%M') ==="
df -h /System/Volumes/Data | tail -1 | awk '{print "boot volume: "$4" free of "$2" ("$5" used)"}'
echo

# --- 1. Plex PhotoTranscoder cache -----------------------------------------
if [ -d "$PLEX_CACHE" ]; then
  size_gb=$(gb_of "$PLEX_CACHE")
  echo "Plex PhotoTranscoder cache: $(human "$PLEX_CACHE") (threshold ${PLEX_TRIM_THRESHOLD_GB}GB)"
  if [ "${size_gb:-0}" -ge "$PLEX_TRIM_THRESHOLD_GB" ]; then
    if [ "$APPLY" = "1" ]; then
      # Delete contents, not the directory - Plex expects it to exist.
      find "$PLEX_CACHE" -mindepth 1 -delete 2>/dev/null
      echo "  -> TRIMMED (regenerates on demand)"
    else
      echo "  -> would trim (run with --apply)"
    fi
  else
    echo "  -> under threshold, leaving alone"
  fi
else
  echo "Plex PhotoTranscoder cache: not present"
fi
echo

# --- 2. Docker reclaimable --------------------------------------------------
if command -v docker >/dev/null 2>&1; then
  echo "Docker reclaimable:"
  docker system df --format '  {{.Type}}: {{.Reclaimable}}' 2>/dev/null
  if [ "$APPLY" = "1" ]; then
    docker image prune -f >/dev/null 2>&1 && echo "  -> pruned dangling images"
    docker builder prune -f >/dev/null 2>&1 && echo "  -> pruned build cache"
  else
    echo "  -> would prune dangling images + build cache (run with --apply)"
  fi
fi
echo

# --- 3. Report other large caches (never auto-deleted) ----------------------
echo "Other large items (reported only, NOT touched):"
for d in "$HOME/Library/Caches" "$HOME/Library/Application Support/Claude"; do
  [ -d "$d" ] && printf "  %-58s %s\n" "$(basename "$d")" "$(human "$d")"
done

echo
df -h /System/Volumes/Data | tail -1 | awk '{print "after: "$4" free ("$5" used)"}'
