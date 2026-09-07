#!/usr/bin/env python3
"""Routes friendly DNS names to LAN appliance admin consoles over HTTPS.

Covers the network hardware that is NOT a container on the Mac Mini:

    nas.kodyparton.com   -> https://192.168.178.38   UniFi UNAS Pro
    ziggo.kodyparton.com -> https://192.168.178.1    Ziggo cable modem/gateway

Two independent pieces, both idempotent, either can be skipped:

  1. Nginx Proxy Manager  -- a proxy host per device, reusing the existing
     *.kodyparton.com wildcard cert (id 1, valid to 2026-10-15). These are the
     only https upstreams in this NPM instance; every container host forwards
     over http. Both appliances present self-signed certs, so the generated
     config disables upstream verification -- client-facing TLS is unaffected
     and still uses the real wildcard cert.
  2. AdGuard Home         -- a DNS rewrite per device -> 192.168.178.69, so the
     names resolve on the LAN alongside the container rewrites already there.

Passwords are prompted for, never taken from argv (which `ps` exposes) and
never written to disk. Stdlib only -- no pip install anywhere.

Usage:
    python3 scripts/add_device_proxy_hosts.py                 # all devices
    python3 scripts/add_device_proxy_hosts.py --device ziggo  # just one
    python3 scripts/add_device_proxy_hosts.py --dry-run       # change nothing
    python3 scripts/add_device_proxy_hosts.py --skip-dns      # NPM only
    python3 scripts/add_device_proxy_hosts.py --skip-npm      # DNS only

If you do not have the AdGuard admin password to hand, use
    --dns-method=file
which stops the container, edits adguard/conf/AdGuardHome.yaml, and starts it
again. That needs no credential but drops LAN DNS for a few seconds -- AdGuard
rewrites its own config on shutdown, so the file cannot safely be edited while
it is running.
"""
import argparse, getpass, json, os, re, ssl, subprocess, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def secret(key, env_var, prompt):
    """Credential resolution order: environment, then Infisical, then prompt.

    Infisical is the stack's central credential store and already holds both
    of these (NPM_ADMIN_PASSWORD, ADGUARD_ADMIN_PASSWORD), so in practice this
    runs unattended. The prompt is the fallback for when Infisical is down or
    the machine-identity credentials are missing -- not the normal path.
    """
    v = os.environ.get(env_var)
    if v:
        return v, "env"
    try:
        from infisical_client import get_secret
        v = get_secret(key)
        if v:
            return v, "infisical"
    except Exception as e:
        print(f"  (Infisical lookup for {key} failed: {e})")
    return getpass.getpass(prompt), "prompt"

# Both appliances answer on :443 with a self-signed cert and accept a foreign
# Host header (measured, not assumed). https upstream is chosen over http even
# where http works, so admin credentials are not carried in the clear across
# the LAN hop between NPM and the device.
DEVICES = [
    {"key": "nas",   "domain": "nas.kodyparton.com",
     "host": "192.168.178.38", "port": 443, "scheme": "https",
     "label": "UniFi UNAS Pro admin console"},
    {"key": "ziggo", "domain": "ziggo.kodyparton.com",
     "host": "192.168.178.1",  "port": 443, "scheme": "https",
     "label": "Ziggo cable modem/gateway admin"},
]

LAN_IP      = "192.168.178.69"
NPM_URL     = os.environ.get("NPM_URL", "http://192.168.178.69:81")
NPM_IDENT   = os.environ.get("NPM_IDENTITY", "admin@example.com")
ADGUARD_URL = os.environ.get("ADGUARD_URL", "http://192.168.178.69:30043")
ADGUARD_USER= os.environ.get("ADGUARD_USERNAME", "admin")
CERT_ID     = int(os.environ.get("NPM_CERT_ID", "1"))
REPO        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# nginx defaults proxy_ssl_verify to off, but the UNAS presents a self-signed
# CN=unifi.local cert, so state it explicitly rather than relying on a default
# a future nginx could change. proxy_ssl_server_name sends SNI, which UniFi OS
# wants. Buffering off keeps the console's streaming endpoints responsive.
ADVANCED_CONFIG = """proxy_ssl_verify off;
proxy_ssl_server_name on;
proxy_buffering off;"""


def req(url, method="GET", data=None, headers=None, timeout=25):
    body = json.dumps(data).encode() if data is not None else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    h.update(headers or {})
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:400]}


def do_npm(dry, devices):
    print("== Nginx Proxy Manager ==")
    pw, src = secret("NPM_ADMIN_PASSWORD", "NPM_PASSWORD", f"  NPM password for {NPM_IDENT}: ")
    if not pw:
        print("  ! no password available, skipping NPM"); return False
    print(f"  credential source: {src}")

    st, tok = req(f"{NPM_URL}/api/tokens", "POST", {"identity": NPM_IDENT, "secret": pw})
    if st != 200 or not tok or "token" not in tok:
        print(f"  ! login failed ({st}): {tok}"); return False
    auth = {"Authorization": f"Bearer {tok['token']}"}
    print("  authenticated.")

    st, hosts = req(f"{NPM_URL}/api/nginx/proxy-hosts", headers=auth)
    if st != 200:
        print(f"  ! could not list proxy hosts ({st}): {hosts}"); return False
    have = {}
    for h in hosts or []:
        for d in (h.get("domain_names") or []):
            have[d] = h

    ok = True
    for dev in devices:
        domain = dev["domain"]
        if domain in have:
            h = have[domain]
            print(f"  = {domain} already exists (id {h['id']}) -> "
                  f"{h['forward_scheme']}://{h['forward_host']}:{h['forward_port']} — leaving alone.")
            continue
        payload = {
            "domain_names": [domain],
            "forward_scheme": dev["scheme"],
            "forward_host": dev["host"],
            "forward_port": dev["port"],
            "certificate_id": CERT_ID,
            "ssl_forced": True,
            "http2_support": True,
            "hsts_enabled": True,
            "hsts_subdomains": False,
            "block_exploits": False,
            "caching_enabled": False,
            "allow_websocket_upgrade": True,   # these consoles are websocket SPAs
            "access_list_id": 0,
            "advanced_config": ADVANCED_CONFIG,
            "locations": [],
            "meta": {},
        }
        if dry:
            print(f"  [dry-run] would create {domain} -> "
                  f"{dev['scheme']}://{dev['host']}:{dev['port']}  ({dev['label']})")
            continue
        st, res = req(f"{NPM_URL}/api/nginx/proxy-hosts", "POST", payload, headers=auth)
        if st not in (200, 201):
            print(f"  ! create failed for {domain} ({st}): {res}"); ok = False; continue
        print(f"  + created proxy host id {res.get('id')}: {domain} -> "
              f"{dev['scheme']}://{dev['host']}:{dev['port']}")
    return ok


def do_dns_api(dry, devices):
    print("== AdGuard Home (API) ==")
    pw, src = secret("ADGUARD_ADMIN_PASSWORD", "ADGUARD_PASSWORD", f"  AdGuard password for {ADGUARD_USER}: ")
    if not pw:
        print("  ! no password available, skipping DNS"); return False
    print(f"  credential source: {src}")
    import base64
    basic = base64.b64encode(f"{ADGUARD_USER}:{pw}".encode()).decode()
    auth = {"Authorization": f"Basic {basic}"}

    st, lst = req(f"{ADGUARD_URL}/control/rewrite/list", headers=auth)
    if st == 401:
        print("  ! login rejected (wrong password). Try --dns-method=file."); return False
    if st != 200:
        print(f"  ! could not list rewrites ({st}): {lst}"); return False
    have = {e.get("domain"): e.get("answer") for e in (lst or [])}

    ok = True
    for dev in devices:
        domain = dev["domain"]
        if domain in have:
            print(f"  = rewrite already present: {domain} -> {have[domain]} — leaving alone.")
            continue
        if dry:
            print(f"  [dry-run] would add rewrite {domain} -> {LAN_IP}"); continue
        st, res = req(f"{ADGUARD_URL}/control/rewrite/add", "POST",
                      {"domain": domain, "answer": LAN_IP}, headers=auth)
        if st != 200:
            print(f"  ! add failed for {domain} ({st}): {res}"); ok = False; continue
        print(f"  + added rewrite {domain} -> {LAN_IP} (no restart needed)")
    return ok


def do_dns_file(dry, devices):
    """Credential-free fallback: stop AdGuard, edit its YAML, start it.

    The stop is not optional. AdGuard writes its running config back to
    AdGuardHome.yaml as it shuts down, so an edit made while it is running is
    silently overwritten on the next restart. Note each entry needs an
    explicit `enabled: true` -- without it the rewrite is silently ignored
    (see docs/containers/adguard.md).
    """
    print("== AdGuard Home (file + restart) ==")
    cfg = os.path.join(REPO, "adguard", "conf", "AdGuardHome.yaml")
    text = open(cfg).read()
    todo = [d for d in devices
            if not re.search(rf"^\s*- domain: {re.escape(d['domain'])}\s*$", text, re.M)]
    for d in devices:
        if d not in todo:
            print(f"  = rewrite already present for {d['domain']} — leaving alone.")
    if not todo:
        return True
    if not re.search(r"^  rewrites:\n", text, re.M):
        print("  ! no 'rewrites:' block found; aborting rather than guessing."); return False

    entries = "".join(f"    - domain: {d['domain']}\n      answer: {LAN_IP}\n      enabled: true\n"
                      for d in todo)
    if dry:
        print(f"  [dry-run] would insert into {cfg}:\n{entries}"); return True

    backup = cfg + ".bak"
    open(backup, "w").write(text)
    print(f"  backed up -> {backup}")
    print("  stopping adguard (LAN DNS is down for a few seconds)...")
    subprocess.run(["docker", "stop", "adguard"], check=True, capture_output=True)
    try:
        text = open(cfg).read()  # re-read: AdGuard rewrote it on shutdown
        m = re.search(r"^  rewrites:\n", text, re.M)
        open(cfg, "w").write(text[:m.end()] + entries + text[m.end():])
        for d in todo:
            print(f"  + inserted rewrite {d['domain']} -> {LAN_IP}")
    finally:
        subprocess.run(["docker", "start", "adguard"], check=True, capture_output=True)
        print("  adguard started.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-npm", action="store_true")
    ap.add_argument("--skip-dns", action="store_true")
    ap.add_argument("--device", choices=[d["key"] for d in DEVICES],
                    help="limit to one device (default: all)")
    ap.add_argument("--dns-method", choices=["api", "file"], default="api")
    a = ap.parse_args()

    devices = [d for d in DEVICES if not a.device or d["key"] == a.device]
    print("Devices: " + ", ".join(f"{d['domain']} -> {d['scheme']}://{d['host']}" for d in devices) + "\n")

    ok = True
    if not a.skip_npm:
        ok &= do_npm(a.dry_run, devices)
    if not a.skip_dns:
        ok &= (do_dns_file if a.dns_method == "file" else do_dns_api)(a.dry_run, devices)

    print("\nDone." if ok else "\nFinished with errors — see above.")
    if not a.dry_run and ok:
        print("Verify:")
        for d in devices:
            print(f"  dig +short {d['domain']} @{LAN_IP} && curl -sS -o /dev/null "
                  f"-w '%{{http_code}}\\n' https://{d['domain']}/")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
