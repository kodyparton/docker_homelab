#!/usr/bin/env python3
"""Enables Authelia SSO (OIDC) on Immich, and optionally resets its admin password.

Background: Authelia has had a fully-formed `immich` OIDC client since the SSO
build-out, and OIDC_CLIENT_SECRET_IMMICH has been sitting in Infisical -- but
Immich's own side was never switched on (`/api/server/features` reported
"oauth": false). This script closes that gap.

It does NOT hardcode Immich's config schema. It GETs the live system config,
merges only the `oauth` keys it means to change, and PUTs the result back, so
keys added or renamed by an Immich upgrade are preserved untouched.

Secrets: the OIDC client secret is read from Infisical and never printed. The
admin password is read from Infisical (IMMICH_ADMIN_PASSWORD) or prompted for,
and is likewise never echoed. The password reset runs as an interactive
`docker exec -it`, so the new password is shown in YOUR terminal only -- it is
never captured by this script or written to a log.

Usage:
    python3 scripts/enable_immich_sso.py --reset-password   # reset, then enable SSO
    python3 scripts/enable_immich_sso.py                    # enable SSO only
    python3 scripts/enable_immich_sso.py --dry-run          # show the diff, change nothing
    python3 scripts/enable_immich_sso.py --store-password   # save admin pw to Infisical
"""
import argparse, getpass, json, os, ssl, subprocess, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

IMMICH_URL   = os.environ.get("IMMICH_URL", "https://photos.kodyparton.com")
ADMIN_EMAIL  = os.environ.get("IMMICH_ADMIN_EMAIL", "admin@example.com")
ISSUER       = os.environ.get("AUTHELIA_ISSUER", "https://auth.kodyparton.com")
CLIENT_ID    = "immich"
CONTAINER    = "immich-server"
ADMIN_BIN    = "/usr/src/app/server/bin/immich-admin"


def infisical(key):
    try:
        from infisical_client import get_secret
        return get_secret(key) or None
    except Exception as e:
        print(f"  (Infisical lookup for {key} failed: {e})")
        return None


def req(url, method="GET", data=None, token=None, timeout=30):
    body = json.dumps(data).encode() if data is not None else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    ctx = ssl.create_default_context()
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


def reset_password():
    """Hand the terminal to immich-admin so the password never touches this process."""
    print("== Reset admin password ==")
    print("  Handing over to immich-admin. Type the new password at its prompt")
    print("  (or leave blank to have one generated and printed).\n")
    rc = subprocess.call(["docker", "exec", "-it", CONTAINER, ADMIN_BIN, "reset-admin-password"])
    print()
    if rc != 0:
        print(f"  ! reset-admin-password exited {rc}"); return False
    print("  Password reset. Note it down now — it is not stored anywhere yet.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset-password", action="store_true")
    ap.add_argument("--store-password", action="store_true",
                    help="save the admin password into Infisical as IMMICH_ADMIN_PASSWORD")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.reset_password and not a.dry_run:
        if not reset_password():
            sys.exit(1)

    # ---- client secret (never printed) ----
    print("== Credentials ==")
    secret = os.environ.get("OIDC_CLIENT_SECRET_IMMICH") or infisical("OIDC_CLIENT_SECRET_IMMICH")
    if not secret:
        print("  ! OIDC_CLIENT_SECRET_IMMICH not available; cannot configure OAuth."); sys.exit(1)
    print(f"  OIDC client secret: loaded ({len(secret)} chars), source Infisical")

    pw, pw_src = os.environ.get("IMMICH_PASSWORD"), "env"
    if not pw:
        pw, pw_src = infisical("IMMICH_ADMIN_PASSWORD"), "infisical"
    if not pw:
        if not sys.stdin.isatty():
            print("  ! no admin password available (not in env, not in Infisical) and")
            print("    stdin is not a terminal, so it cannot be prompted for.")
            print("    Run this from an interactive shell, or set IMMICH_PASSWORD.")
            sys.exit(1)
        pw, pw_src = getpass.getpass(f"  Immich admin password for {ADMIN_EMAIL}: "), "prompt"
    if not pw:
        print("  ! no admin password; cannot authenticate."); sys.exit(1)
    print(f"  Immich admin password: source {pw_src}")

    # ---- authenticate ----
    st, res = req(f"{IMMICH_URL}/api/auth/login", "POST",
                  {"email": ADMIN_EMAIL, "password": pw})
    if st != 201 and st != 200:
        print(f"  ! login failed ({st}): {res}")
        print("    If you just reset the password, use the new one.")
        sys.exit(1)
    token = res.get("accessToken")
    if not token:
        print(f"  ! no accessToken in login response: {res}"); sys.exit(1)
    print("  authenticated to Immich.")

    # ---- read-modify-write the system config ----
    print("\n== System config ==")
    st, cfg = req(f"{IMMICH_URL}/api/system-config", token=token)
    if st != 200 or not isinstance(cfg, dict):
        print(f"  ! could not read system config ({st}): {cfg}"); sys.exit(1)

    oauth = dict(cfg.get("oauth") or {})
    before = {k: oauth.get(k) for k in ("enabled", "issuerUrl", "clientId", "buttonText", "autoRegister")}

    # Only the keys we mean to change. Everything else Immich returned is kept
    # exactly as-is, so an upgrade that adds keys will not have them clobbered.
    oauth.update({
        "enabled": True,
        "issuerUrl": f"{ISSUER}/.well-known/openid-configuration",
        "clientId": CLIENT_ID,
        "clientSecret": secret,
        # Matches the Authelia client: scopes ['openid','profile','email'],
        # userinfo_signed_response_alg 'none', token_endpoint_auth_method
        # 'client_secret_post'.
        "scope": "openid profile email",
        "profileSigningAlgorithm": "none",
        "signingAlgorithm": "RS256",
        "tokenEndpointAuthMethod": "client_secret_post",
        "buttonText": "Login with Authelia",
        # Auto-register is safe here because the Authelia account `kody` carries
        # the SAME email as the existing Immich admin, so the first SSO login
        # links to that account rather than creating a second one. Verified
        # both sides before enabling.
        "autoRegister": True,
        # Left off deliberately: with autoLaunch the login page immediately
        # bounces to Authelia, which locks you out of password login if SSO
        # ever breaks. Turn it on later once SSO is proven.
        "autoLaunch": False,
    })
    cfg["oauth"] = oauth
    # Keep password login on as the escape hatch.
    if isinstance(cfg.get("passwordLogin"), dict):
        cfg["passwordLogin"]["enabled"] = True

    after = {k: oauth.get(k) for k in ("enabled", "issuerUrl", "clientId", "buttonText", "autoRegister")}
    print(f"  before: {json.dumps(before)}")
    print(f"  after : {json.dumps(after)}   (clientSecret set, not shown)")

    if a.dry_run:
        print("\n[dry-run] no changes written."); sys.exit(0)

    st, res = req(f"{IMMICH_URL}/api/system-config", "PUT", cfg, token=token)
    if st not in (200, 201):
        print(f"  ! config update failed ({st}): {res}"); sys.exit(1)
    print("  system config updated.")

    # ---- verify from the public endpoint, not from our own write ----
    st, feats = req(f"{IMMICH_URL}/api/server/features")
    print("\n== Verify ==")
    if st == 200 and isinstance(feats, dict):
        print(f"  oauth={feats.get('oauth')}  passwordLogin={feats.get('passwordLogin')}")
        if not feats.get("oauth"):
            print("  ! oauth still reports false — check Immich logs."); sys.exit(1)
    else:
        print(f"  ! could not read features ({st})"); sys.exit(1)

    if a.store_password:
        try:
            from infisical_client import set_secret
            set_secret("IMMICH_ADMIN_PASSWORD", pw, comment="Immich admin login (reset 2026-08-30)")
            print("  stored IMMICH_ADMIN_PASSWORD in Infisical.")
        except Exception as e:
            print(f"  ! could not store password in Infisical: {e}")

    print(f"\nDone. Open {IMMICH_URL} — a 'Login with Authelia' button should now appear.")
    print("Password login is still enabled as a fallback; autoLaunch is off on purpose.")


if __name__ == "__main__":
    main()
