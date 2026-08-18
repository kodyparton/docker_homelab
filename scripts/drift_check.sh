#!/bin/bash
# Compares each service's declared compose.yml state against the actual running
# container on this host. Read-only: never starts, stops, or pulls anything.
# Outputs a single JSON array to stdout.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

first=true
seen_containers=""
echo -n "["

while IFS= read -r compose_file; do
  dir="$(dirname "$compose_file")"
  cfg_json="$(cd "$dir" && docker compose -f "$(basename "$compose_file")" config --format json 2>/dev/null)"
  [ -z "$cfg_json" ] && continue

  services="$(echo "$cfg_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(d.get('services',{}).keys()))" 2>/dev/null)"
  [ -z "$services" ] && continue

  while IFS= read -r svc; do
    [ -z "$svc" ] && continue

    svc_line="$(echo "$cfg_json" | python3 -c "
import json,sys
d = json.load(sys.stdin)
s = d['services']['$svc']
print((s.get('container_name') or '') + '|' + (s.get('image') or ''))
" 2>/dev/null)"
    container_name="${svc_line%%|*}"
    expected_image="${svc_line#*|}"

    project="$(basename "$dir" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g')"
    if [ -z "$container_name" ]; then
      container_name="${project}-${svc}-1"
    fi

    # avoid double-reporting the same physical container (e.g. duplicate compose files)
    case " $seen_containers " in
      *" $container_name "*) continue ;;
    esac
    seen_containers="$seen_containers $container_name"

    inspect="$(docker inspect --format '{{.State.Status}}|{{.Config.Image}}|{{.Image}}' "$container_name" 2>/dev/null)"
    if [ -z "$inspect" ]; then
      status="not_found"
      actual_image=""
      container_image_id=""
    else
      status="${inspect%%|*}"
      rest="${inspect#*|}"
      actual_image="${rest%%|*}"
      container_image_id="${rest#*|}"
    fi

    local_image_id=""
    if [ -n "$expected_image" ]; then
      local_image_id="$(docker image inspect "$expected_image" --format '{{.Id}}' 2>/dev/null)"
    fi

    drift="false"
    reason=""
    if [ "$status" != "running" ]; then
      drift="true"
      reason="not_running"
    elif [ -n "$local_image_id" ] && [ "$local_image_id" != "$container_image_id" ]; then
      drift="true"
      reason="image_id_mismatch"
    elif [ -z "$local_image_id" ]; then
      reason="local_image_not_pulled_cannot_verify"
    fi

    if [ "$first" = true ]; then first=false; else echo -n ","; fi
    drift_py="False"; [ "$drift" = "true" ] && drift_py="True"
    python3 -c "
import json
print(json.dumps({
  'service': '$svc',
  'dir': '$dir'.replace('$REPO_ROOT/', ''),
  'containerName': '$container_name',
  'expectedImage': '$expected_image',
  'actualImage': '$actual_image',
  'containerStatus': '$status',
  'drift': $drift_py,
  'reason': '$reason'
}), end='')
"
  done <<< "$services"
done < <(find "$REPO_ROOT" -iname "compose.yml" -not -path "*/.git/*")

echo -n "]"
