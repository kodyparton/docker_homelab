#!/bin/bash
# Checks TLS certificate expiry for each configured host, and domain
# registration expiry (via RDAP) for the apex domain. Read-only.
# Outputs a single JSON array to stdout.
set -uo pipefail

# name|host|port
TLS_TARGETS=(
  "kodyparton.com (apex)|kodyparton.com|443"
  "n8n.kodyparton.com|n8n.kodyparton.com|443"
  "request.kodyparton.com|request.kodyparton.com|443"
  "downloads.kodyparton.com|downloads.kodyparton.com|443"
)
APEX_DOMAIN="kodyparton.com"

classify() {
  local days=$1
  if [ "$days" -le 7 ]; then echo "URGENT"
  elif [ "$days" -le 14 ]; then echo "WARNING"
  elif [ "$days" -le 30 ]; then echo "NOTICE"
  else echo "OK"
  fi
}

first=true
echo -n "["

for entry in "${TLS_TARGETS[@]}"; do
  IFS='|' read -r name host port <<< "$entry"

  if [ "$first" = true ]; then first=false; else echo -n ","; fi

  python3 -c "
import json, socket, ssl
from datetime import datetime, timezone

name = '$name'; host = '$host'; port = $port

def classify(days):
    if days <= 7: return 'URGENT'
    if days <= 14: return 'WARNING'
    if days <= 30: return 'NOTICE'
    return 'OK'

try:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
    not_after = cert['notAfter']
    exp = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
    days_left = (exp - datetime.now(timezone.utc)).days
    print(json.dumps({'type':'tls','name':name,'host':host,'expiresOn':not_after,'daysLeft':days_left,'severity':classify(days_left),'note':''}), end='')
except Exception as e:
    print(json.dumps({'type':'tls','name':name,'host':host,'expiresOn':None,'daysLeft':None,'severity':'ERROR','note':f'could not retrieve certificate: {e}'}), end='')
"
done

# Domain registration expiry via RDAP (no auth required)
rdap_json="$(curl -sL --max-time 10 "https://rdap.org/domain/$APEX_DOMAIN")"
exp_date="$(echo "$rdap_json" | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    for e in d.get('events', []):
        if e.get('eventAction') == 'expiration':
            print(e.get('eventDate',''))
            break
except Exception:
    pass
" 2>/dev/null)"

echo -n ","
if [ -z "$exp_date" ]; then
  python3 -c "
import json
print(json.dumps({'type':'domain','name':'$APEX_DOMAIN registration','host':'$APEX_DOMAIN','expiresOn':None,'daysLeft':None,'severity':'ERROR','note':'could not retrieve RDAP expiration data'}), end='')
"
else
  days_left=$(python3 -c "
from datetime import datetime, timezone
d = datetime.fromisoformat('$exp_date'.replace('Z','+00:00'))
print((d - datetime.now(timezone.utc)).days)
" 2>/dev/null)
  [ -z "$days_left" ] && days_left=999
  severity=$(classify "$days_left")
  python3 -c "
import json
print(json.dumps({'type':'domain','name':'$APEX_DOMAIN registration','host':'$APEX_DOMAIN','expiresOn':'$exp_date','daysLeft':$days_left,'severity':'$severity','note':''}), end='')
"
fi

echo -n "]"
