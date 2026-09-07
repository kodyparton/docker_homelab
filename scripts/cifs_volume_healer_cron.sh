#!/bin/bash
# launchd wrapper around cifs_volume_health_check.sh.
#
# Exists so the healer can run on a short interval without either (a) the
# broken `Mac Mini SSH` / placeholder-Discord n8n credentials in its path, or
# (b) 288 lines a day of `{"ok":true}` in the log. Only non-`ok` runs are
# recorded, so anything in this log is a real event worth reading.
#
# Install: see docs/architecture/automation.md ("NAS volume self-healer").
set -u

REPO="/Users/kp-srv-01/Documents/docker"
LOG="${LOG:-$REPO/cifs_volume_healer.log}"

out="$(bash "$REPO/scripts/cifs_volume_health_check.sh" 2>&1)"
status="$(printf '%s' "$out" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("status","unparseable"))
except Exception: print("unparseable")' 2>/dev/null || echo unparseable)"

# A quiet, healthy run is the overwhelmingly common case -- say nothing.
[ "$status" = "ok" ] && exit 0

printf '%s %s\n' "$(date -Iseconds)" "$out" >> "$LOG"

# Keep the log bounded; this runs unattended and indefinitely.
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 500 ]; then
  tail -n 250 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
