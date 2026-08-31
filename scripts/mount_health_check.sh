#!/bin/bash
# Read-only check: is /Volumes/media the live SMB mount, or has a stale stub
# shadowed it?
#
# History: this script used to also check 8 containers' bind-mounted SMB
# paths (sonarr/sonarr-4k/radarr/radarr-4k/qbittorrent/immich-server/
# lazylibrarian/audiobookshelf), which went through macOS host passthrough
# and could drop (ENOENT) or get shadowed by a stale mountpoint. As of
# 2026-08-29, all 8 were migrated to native Linux CIFS volumes mounted
# directly by Docker inside OrbStack's VM (see docs/architecture/
# known-issues.md, "SMB mount passthrough — RESOLVED 2026-08-29") -- they no
# longer touch /Volumes/media or macOS's smbfs client at all, so neither
# failure mode below applies to them anymore.
#
# The one remaining consumer of the host-passthrough mount is Plex --
# a native macOS app, not a container, so it was never in the CHECKS list
# here to begin with (it can't be docker-restarted). This script still
# matters for Plex's sake: on an SMB reconnect (sleep/wake or network
# blip), macOS can find a stale leftover directory still sitting at
# /Volumes/media (left behind by an unclean unmount) and mount the fresh
# share as /Volumes/media-1 instead of reusing the canonical path -- Plex's
# library sections are hardcoded to /Volumes/media/... in its own database,
# so this silently breaks it (see the 2026-08-27 "media unavailable"
# incident, which sat broken for 2+ hours). Fix is a one-time
# `sudo rmdir /Volumes/media` (only root can touch /Volumes) then
# reconnecting the share -- this script only detects and reports it.
#
# This script only detects; remediation (the sudo command above) is a human
# task, not automatable from here.
#
# Extended 2026-08-31 while diagnosing "Plex load times vary and sometimes hang
# entirely". The shadow check below only ever caught one of three ways this
# mount fails Plex, and it is the *least* likely of the three to be the cause
# of a hang:
#   - host_mount_shadowed    -- the 2026-08-27 case; Plex reads an empty stub
#   - host_mount_missing     -- share simply not mounted; Plex errors fast
#   - host_mount_unresponsive-- mounted and present, but reads block. THIS is
#     the hang signature: an SMB share whose server stopped answering leaves
#     the client wedged in an uninterruptible read rather than returning an
#     error, so Plex's scanner/UI thread blocks on stat() and the app appears
#     to freeze while `mount` still cheerfully lists it as healthy. Detecting
#     it requires actually attempting a read under a timeout -- presence
#     checks alone (`mount | grep`, `test -d`) all pass in this state, which
#     is exactly why the original script reported "ok" through it.
#
# macOS ships no timeout(1)/gtimeout(1), so the probe timeout is implemented
# in-shell (background the read, poll, SIGKILL on expiry).
#
# NOT covered here: containers stuck because Docker itself could not mount a
# native CIFS volume (a third, distinct failure mode, introduced by the
# 2026-08-29 migration and first seen 2026-08-30). That one fails at container
# *creation*, so `restart: always` never fires and the container stays dead
# indefinitely -- see scripts/cifs_volume_health_check.sh, which detects and
# actually remediates it.
set -u

MOUNT_POINT="${MOUNT_POINT:-/Volumes/media}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-10}"

# Run "$@" with a hard timeout. Returns 124 if it had to be killed.
# Deliberately SIGKILL, not SIGTERM: a process blocked in an unresponsive SMB
# read is in uninterruptible I/O and will ignore a catchable signal, which is
# the exact state we are trying to detect.
run_with_timeout() {
  timeout_secs="$1"; shift
  "$@" >/dev/null 2>&1 &
  probe_pid=$!
  waited=0
  while kill -0 "$probe_pid" 2>/dev/null; do
    if [ "$waited" -ge "$timeout_secs" ]; then
      kill -9 "$probe_pid" 2>/dev/null
      wait "$probe_pid" 2>/dev/null
      return 124
    fi
    sleep 1
    waited=$((waited + 1))
  done
  wait "$probe_pid"
}

is_mounted="false"
mount | grep -q "on ${MOUNT_POINT} (smbfs" && is_mounted="true"

has_shadow_sibling="false"
ls -d "${MOUNT_POINT}"-[0-9]* >/dev/null 2>&1 && has_shadow_sibling="true"

status="ok"; ok="true"; detail=""

if [ "$is_mounted" != "true" ]; then
  # Not the live smbfs mount. Which of the two failure shapes is it?
  if [ "$has_shadow_sibling" = "true" ]; then
    status="host_mount_shadowed"; ok="false"
    detail="a stale directory occupies ${MOUNT_POINT} and the real share mounted alongside it; fix: sudo rmdir ${MOUNT_POINT} then reconnect the share"
  else
    status="host_mount_missing"; ok="false"
    detail="${MOUNT_POINT} is not mounted; fix: open smb://192.168.178.38/media to reconnect via the saved credential"
  fi
else
  # Mounted -- but is it actually answering? Presence is not health.
  if run_with_timeout "$PROBE_TIMEOUT" ls "${MOUNT_POINT}"; then
    status="ok"; ok="true"
  else
    status="host_mount_unresponsive"; ok="false"
    detail="${MOUNT_POINT} is mounted but a directory read did not return within ${PROBE_TIMEOUT}s; Plex will appear frozen in this state"
  fi
fi

if [ -n "$detail" ]; then
  echo "{\"check\":\"host_media_mount\",\"ok\":$ok,\"status\":\"$status\",\"detail\":\"$detail\"}"
else
  echo "{\"check\":\"host_media_mount\",\"ok\":$ok,\"status\":\"$status\"}"
fi
