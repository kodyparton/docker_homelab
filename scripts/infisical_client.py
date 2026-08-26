#!/usr/bin/env python3
"""
Thin client for this homelab's Infisical instance (docs/containers/infisical.md).
Authenticates as the "homelab-automation" machine identity (Universal Auth) -
credentials read from scripts/.infisical_credentials, gitignored, never
printed. All secrets live in the "Homelab Secrets" project, "prod"
environment, flat (no folders) unless a --path is given.

Usage:
    python3 scripts/infisical_client.py list
    python3 scripts/infisical_client.py get SONARR_API_KEY
    python3 scripts/infisical_client.py set SONARR_API_KEY <value>
    python3 scripts/infisical_client.py set SONARR_API_KEY <value> --comment "rotated 2026-08-26"
    python3 scripts/infisical_client.py delete SOME_OLD_KEY

Importable too:
    from infisical_client import get_secret, set_secret, list_secrets, delete_secret
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = REPO_ROOT / "scripts" / ".infisical_credentials"
BASE_URL = "http://192.168.178.69:30034"
PROJECT_ID = "12b81f55-e5b6-4296-93ea-b96879f6ef65"  # "Homelab Secrets" - not sensitive, just an id
ENVIRONMENT = "prod"

_token_cache = None


def _read_creds():
    if not CREDS_FILE.exists():
        print(f"No credentials at {CREDS_FILE} - see docs/architecture/secrets-and-rotation.md")
        sys.exit(1)
    creds = {}
    for line in CREDS_FILE.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    return creds["CLIENT_ID"], creds["CLIENT_SECRET"]


def _token():
    global _token_cache
    if _token_cache:
        return _token_cache
    client_id, client_secret = _read_creds()
    body = json.dumps({"clientId": client_id, "clientSecret": client_secret}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/universal-auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        _token_cache = json.load(resp)["accessToken"]
    return _token_cache


def _request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Infisical API {method} {path} -> {e.code}: {e.read().decode()}")


def list_secrets(secret_path="/"):
    """Returns {key: value} for every secret at this path."""
    q = f"?workspaceId={PROJECT_ID}&environment={ENVIRONMENT}&secretPath={secret_path}"
    result = _request("GET", f"/api/v3/secrets/raw{q}")
    return {s["secretKey"]: s["secretValue"] for s in result.get("secrets", [])}


def get_secret(key, secret_path="/"):
    q = f"?workspaceId={PROJECT_ID}&environment={ENVIRONMENT}&secretPath={secret_path}"
    result = _request("GET", f"/api/v3/secrets/raw/{key}{q}")
    return result["secret"]["secretValue"]


def set_secret(key, value, secret_path="/", comment=""):
    """Creates the secret if it doesn't exist, updates it if it does."""
    body = {
        "workspaceId": PROJECT_ID,
        "environment": ENVIRONMENT,
        "secretPath": secret_path,
        "secretValue": value,
        "type": "shared",
        "secretComment": comment,
    }
    try:
        return _request("POST", f"/api/v3/secrets/raw/{key}", body)
    except RuntimeError as e:
        if "already exist" in str(e).lower():
            return _request("PATCH", f"/api/v3/secrets/raw/{key}", body)
        raise


def delete_secret(key, secret_path="/"):
    body = {"workspaceId": PROJECT_ID, "environment": ENVIRONMENT, "secretPath": secret_path}
    return _request("DELETE", f"/api/v3/secrets/raw/{key}", body)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        for k in sorted(list_secrets().keys()):
            print(k)
    elif cmd == "get" and len(sys.argv) >= 3:
        print(get_secret(sys.argv[2]))
    elif cmd == "set" and len(sys.argv) >= 4:
        comment = ""
        if "--comment" in sys.argv:
            comment = sys.argv[sys.argv.index("--comment") + 1]
        set_secret(sys.argv[2], sys.argv[3], comment=comment)
        print(f"Set {sys.argv[2]}")
    elif cmd == "delete" and len(sys.argv) >= 3:
        delete_secret(sys.argv[2])
        print(f"Deleted {sys.argv[2]}")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
