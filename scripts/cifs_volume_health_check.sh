#!/bin/bash
# Detect-and-heal: containers that died because Docker could not mount their
# native CIFS (NAS) volume, and are now stuck with no hope of self-recovery.
#
# Built 2026-08-30 after a real incident: at 09:21:56Z the NAS at
# 192.168.178.38 briefly went unreachable, and all 9 containers holding a
# native CIFS volume (sonarr, sonarr-4k, radarr, radarr-4k, unpackerr,
# qbittorrent, lazylibrarian, audiobookshelf, immich-server) died together
# with exit code 255. They then sat dead for 2+ hours after the NAS came
# back, until a human noticed.
#
# Why `restart: always` does NOT cover this -- the important bit. A volume
# mount failure happens at container *creation*, before the entrypoint ever
# runs. It is not a process exit, so the restart policy is never consulted:
# Docker gives up permanently and the container stays down indefinitely,
# even once the NAS is healthy again. The error is only visible in
# `docker inspect .State.Error`, never in `docker logs` -- the application
# logs just stop mid-stream, looking perfectly healthy right up to the cut.
#
# This is a DIFFERENT failure mode from the two in mount_health_check.sh,
# and it is the one created by the 2026-08-29 migration off macOS host
# passthrough onto native Linux CIFS volumes (see docs/architecture/
# known-issues.md, "SMB mount passthrough -- RESOLVED 2026-08-29"). That
# migration retired the old per-container watch list as obsolete, which was
# correct for the *old* passthrough modes but left this new
# CIFS-mount-at-create mode uncovered. This script closes that gap.
#
# Unlike its siblings, this script REMEDIATES rather than only reporting,
# because here a plain `docker start` is the complete and correct fix (it
# re-attempts the CIFS mount, which succeeds once the NAS answers) and it
# needs no sudo and no host-level surgery. Contrast the `host_mount_shadowed`
# case in mount_health_check.sh, where restarting is provably useless and the
# real fix needs root.
#
# Safety properties:
#   - Only ever touches containers whose recorded .State.Error is a volume
#     mount failure. Anything running, healthy, or dead for its own unrelated
#     reasons is never touched.
#   - Will not restart a container while its NAS is still unreachable; that
#     would just burn failed starts and thrash. Reachability is probed per
#     distinct NAS host, so one dead NAS can't gate healing for another.
#   - DRY_RUN=1 detects and reports without touching anything.
set -u

DRY_RUN="${DRY_RUN:-0}"
NAS_PROBE_PORT="${NAS_PROBE_PORT:-445}"
NAS_PROBE_TIMEOUT="${NAS_PROBE_TIMEOUT:-5}"
SETTLE_SECONDS="${SETTLE_SECONDS:-6}"

if ! docker info >/dev/null 2>&1; then
  echo '{"check":"cifs_volume_mounts","ok":false,"status":"docker_unavailable","stuck_count":0,"restarted":0,"containers":[]}'
  exit 0
fi

# Collect every container, then keep only those whose recorded error is a
# volume-mount failure. .State.Error is cleared by Docker on a successful
# start, so a healthy container can never match here (verified 2026-08-30).
#
# Both `exited` AND `created` states must be considered. A container that was
# running when the NAS dropped ends up `exited` (the 2026-08-30 incident),
# but one that never came up even once -- e.g. the fresh replacement
# Watchtower builds during an image update, or anything just brought up by
# `compose up` -- is left in `created` and would otherwise be missed
# entirely. Filtering on exit status alone silently skipped that second case.
all_ids="$(docker ps -aq 2>/dev/null)"
if [ -z "$all_ids" ]; then
  echo '{"check":"cifs_volume_mounts","ok":true,"status":"ok","stuck_count":0,"restarted":0,"containers":[]}'
  exit 0
fi

# shellcheck disable=SC2086
stuck_json="$(docker inspect $all_ids 2>/dev/null | python3 -c '
import sys, json, re

try:
    conts = json.load(sys.stdin)
except Exception:
    print("[]"); sys.exit()

out = []
for c in conts:
    state = c.get("State") or {}
    status = state.get("Status")
    # Never touch anything currently running or on its way up.
    if status not in ("exited", "created"):
        continue
    err = state.get("Error") or ""
    # Match the mount failure specifically, so a container that merely exited
    # non-zero for its own reasons is left alone.
    if "failed to mount local volume" not in err and "error while mounting volume" not in err:
        continue

    name = (c.get("Name") or "").lstrip("/")
    m = re.search(r"/volumes/([^/]+)/_data", err)
    vol = m.group(1) if m else None
    m = re.search(r"//([A-Za-z0-9._-]+)/", err)
    host = m.group(1) if m else None
    # Watchtower renames a container to <shortid>_<name> as the first step of
    # an update; if creating the replacement then fails on this same mount
    # error, the rename is left half-applied and the real name goes missing.
    # Reported, not auto-fixed: restarting under the mangled name still fully
    # restores service, and renaming back is a judgement call for a human.
    renamed = bool(re.match(r"^[0-9a-f]{12}_", name))

    out.append({
        "container": name,
        "volume": vol,
        "nas_host": host,
        "exit_code": state.get("ExitCode"),
        "state_before": status,
        "watchtower_rename_leftover": renamed,
    })

print(json.dumps(out))
')"

[ -z "$stuck_json" ] && stuck_json="[]"
stuck_count="$(printf '%s' "$stuck_json" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)"

if [ "$stuck_count" -eq 0 ]; then
  echo '{"check":"cifs_volume_mounts","ok":true,"status":"ok","stuck_count":0,"restarted":0,"containers":[]}'
  exit 0
fi

# Probe each distinct NAS host once. A container whose NAS is still down is
# skipped rather than pointlessly restarted.
hosts="$(printf '%s' "$stuck_json" | python3 -c '
import sys, json
seen = []
for c in json.load(sys.stdin):
    h = c.get("nas_host")
    if h and h not in seen:
        seen.append(h)
print("\n".join(seen))
')"

reach=""
while IFS= read -r h; do
  [ -z "$h" ] && continue
  if nc -z -G "$NAS_PROBE_TIMEOUT" -w "$NAS_PROBE_TIMEOUT" "$h" "$NAS_PROBE_PORT" >/dev/null 2>&1; then
    reach="${reach}${h}|true
"
  else
    reach="${reach}${h}|false
"
  fi
done <<EOF
$hosts
EOF

# Decide, per container, whether to attempt a restart.
plan="$(printf '%s' "$stuck_json" | REACH="$reach" DRY_RUN="$DRY_RUN" python3 -c '
import sys, json, os

reach = {}
for line in os.environ.get("REACH", "").splitlines():
    if "|" in line:
        h, v = line.split("|", 1)
        reach[h] = (v == "true")

dry = os.environ.get("DRY_RUN") == "1"
for c in json.load(sys.stdin):
    host = c.get("nas_host")
    # Unknown host means the error text did not parse; attempt anyway rather
    # than stranding the container, the start itself is the real test.
    up = reach.get(host, True) if host else True
    if dry:
        action = "dry_run"
    elif up:
        action = "attempt"
    else:
        action = "skipped_nas_down"
    print(c["container"] + "|" + action)
')"

results=""
while IFS='|' read -r name action; do
  [ -z "$name" ] && continue
  if [ "$action" != "attempt" ]; then
    results="${results}${name}|${action}|
"
    continue
  fi
  if start_err="$(docker start "$name" 2>&1 >/dev/null)"; then
    results="${results}${name}|started|
"
  else
    # Collapse to one line; the JSON stage re-associates by container name.
    results="${results}${name}|start_failed|$(printf '%s' "$start_err" | tr '\n' ' ' | sed 's/password=[^,]*/password=***/')
"
  fi
done <<EOF
$plan
EOF

# Give the containers a moment to either hold or fall over again.
case "$results" in
  *"|started|"*) sleep "$SETTLE_SECONDS" ;;
esac

final=""
while IFS= read -r name; do
  [ -z "$name" ] && continue
  final="${final}${name}|$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo unknown)
"
done <<EOF
$(printf '%s' "$stuck_json" | python3 -c 'import sys,json; print("\n".join(c["container"] for c in json.load(sys.stdin) if c.get("container")))')
EOF

printf '%s' "$stuck_json" | RESULTS="$results" FINAL="$final" REACH="$reach" python3 -c '
import sys, json, os

def parse(blob, fields):
    out = {}
    for line in blob.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        out[parts[0]] = dict(zip(fields, parts[1:]))
    return out

actions = parse(os.environ.get("RESULTS", ""), ["action", "error"])
finals = parse(os.environ.get("FINAL", ""), ["state"])
reach = {}
for line in os.environ.get("REACH", "").splitlines():
    if "|" in line:
        h, v = line.split("|", 1)
        reach[h] = (v == "true")

containers = []
healed = attempted = skipped = 0
for info in json.load(sys.stdin):
    name = info["container"]
    action = actions.get(name, {}).get("action", "not_attempted")
    state = finals.get(name, {}).get("state", "unknown")
    recovered = state == "running"

    if action == "started":
        attempted += 1
    elif action == "start_failed":
        attempted += 1
    elif action == "skipped_nas_down":
        skipped += 1
    if recovered:
        healed += 1

    entry = dict(info)
    entry["action"] = action
    entry["state_after"] = state
    entry["recovered"] = recovered
    err = actions.get(name, {}).get("error")
    if err:
        entry["error"] = err[:300]
    containers.append(entry)

total = len(containers)
if os.environ.get("RESULTS") and all(c["action"] == "dry_run" for c in containers):
    status, ok = "dry_run", False
elif skipped == total:
    status, ok = "nas_unreachable", False
elif healed == total:
    status, ok = "healed", True
elif healed:
    status, ok = "partially_healed", False
else:
    status, ok = "heal_failed", False

print(json.dumps({
    "check": "cifs_volume_mounts",
    "ok": ok,
    "status": status,
    "nas_hosts": reach,
    "stuck_count": total,
    "restarted": healed,
    "skipped_nas_down": skipped,
    "containers": containers,
}))'
