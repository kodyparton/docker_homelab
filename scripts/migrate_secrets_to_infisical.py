#!/usr/bin/env python3
"""
One-time (or re-runnable) migration: pulls real secret values out of the
per-service .env files that actually hold them and pushes them into
Infisical under clear, service-prefixed names. Read-only against the
.env files - never writes back to them.

Only migrates .env files/keys that are genuinely secrets. Deliberately
skips non-secret config (timezone, domain, timeouts) and anything that
only ever existed inside n8n's own encrypted credential store, since
n8n's API never exposes stored credential values for reading - those
need to be re-entered by hand if they're ever wanted in Infisical too
(see docs/architecture/secrets-and-rotation.md).

Usage:
    python3 scripts/migrate_secrets_to_infisical.py
"""
from pathlib import Path

from infisical_client import set_secret

REPO_ROOT = Path(__file__).resolve().parent.parent

# (env file relative to repo root, env var name, Infisical key name, comment)
SOURCES = [
    ("homepage/.env", "HOMEPAGE_VAR_SONARR_API_KEY", "SONARR_API_KEY", "sonarr"),
    ("homepage/.env", "HOMEPAGE_VAR_SONARR_4K_API_KEY", "SONARR_4K_API_KEY", "sonarr-4k"),
    ("homepage/.env", "HOMEPAGE_VAR_RADARR_API_KEY", "RADARR_API_KEY", "radarr"),
    ("homepage/.env", "HOMEPAGE_VAR_RADARR_4K_API_KEY", "RADARR_4K_API_KEY", "radarr-4k"),
    ("homepage/.env", "HOMEPAGE_VAR_PROWLARR_API_KEY", "PROWLARR_API_KEY", "prowlarr"),
    ("homepage/.env", "HOMEPAGE_VAR_OVERSEERR_API_KEY", "OVERSEERR_API_KEY", "overseerr"),
    ("homepage/.env", "HOMEPAGE_VAR_TAUTULLI_API_KEY", "TAUTULLI_API_KEY", "tautulli"),
    ("homepage/.env", "HOMEPAGE_VAR_QBITTORRENT_USERNAME", "QBITTORRENT_USERNAME", "qbittorrent"),
    ("homepage/.env", "HOMEPAGE_VAR_QBITTORRENT_PASSWORD", "QBITTORRENT_PASSWORD", "qbittorrent - weak, worth rotating for real (see known-issues.md)"),
    ("vikunja/.env", "VIKUNJA_JWT_SECRET", "VIKUNJA_JWT_SECRET", "vikunja session-signing secret"),
    ("brain-bot/.env", "DISCORD_BOT_TOKEN", "BRAIN_BOT_DISCORD_TOKEN", "second brain's Discord bot token"),
    ("scripts/.n8n_api_key", None, "N8N_API_KEY", "n8n public API key (whole-file value, not KEY=VALUE)"),
]


def read_env_value(path: Path, var_name: str) -> str:
    for line in path.read_text().splitlines():
        if line.startswith(f"{var_name}="):
            return line.split("=", 1)[1].strip()
    raise KeyError(f"{var_name} not found in {path}")


def main():
    migrated = []
    for rel_path, var_name, infisical_key, comment in SOURCES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            print(f"  skip {infisical_key}: {rel_path} does not exist")
            continue
        value = path.read_text().strip() if var_name is None else read_env_value(path, var_name)
        set_secret(infisical_key, value, comment=comment)
        migrated.append(infisical_key)
        print(f"  migrated {infisical_key} (from {rel_path})")

    print(f"\nDone. {len(migrated)} secrets migrated into Infisical's 'Homelab Secrets' project (prod).")


if __name__ == "__main__":
    main()
