#!/usr/bin/env python3
"""Writes this stack's settings into Mylar3's config.ini. Idempotent.

    docker compose -f mylar3/compose.yml stop
    python3 scripts/configure_mylar3.py
    docker compose -f mylar3/compose.yml start

Run it with the container STOPPED, or Mylar may write its in-memory config
back over the edit. Only the keys below are touched; everything else in the
file (including the Torznab providers Prowlarr syncs in) is kept.

Secrets come from Infisical and are never printed: COMICVINE_API_KEY,
QBITTORRENT_USERNAME, QBITTORRENT_PASSWORD, and MYLAR_API_KEY, which is
generated and stored on the first run. Key names and sections match Mylar's
mylar/config.py; TORRENT_DOWNLOADER 5 means qBittorrent.
"""
import configparser
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infisical_client import get_secret, set_secret  # noqa: E402

INI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "mylar3", "config", "mylar", "config.ini")


def mylar_api_key():
    try:
        return get_secret("MYLAR_API_KEY")
    except Exception:
        key = secrets.token_hex(16)
        set_secret("MYLAR_API_KEY", key, comment="Mylar3 API key: Prowlarr app sync + Homepage widget")
        print("MYLAR_API_KEY generated and stored in Infisical")
        return key


def main():
    if not os.path.exists(INI):
        sys.exit(f"{INI} not found: start Mylar3 once so it writes its default config, then stop it.")
    cfg = configparser.RawConfigParser()
    cfg.optionxform = str  # keep Mylar's key spelling
    cfg.read(INI)
    want = {
        "General": {"destination_dir": "/comics"},
        # copy, not move: qBittorrent keeps seeding and removes the files itself
        # when its global share limits are hit.
        "PostProcess": {"post_processing": "True", "file_opts": "copy",
                        "enable_check_folder": "True", "check_folder": "/mnt/downloads/comics"},
        "API": {"api_enabled": "True", "api_key": mylar_api_key()},
        "CV": {"comicvine_api": get_secret("COMICVINE_API_KEY")},
        "Client": {"torrent_downloader": "5"},
        "qBittorrent": {"qbittorrent_host": "http://192.168.178.69:30024",
                        "qbittorrent_username": get_secret("QBITTORRENT_USERNAME"),
                        "qbittorrent_password": get_secret("QBITTORRENT_PASSWORD"),
                        "qbittorrent_label": "comics",
                        "qbittorrent_loadaction": "default"},
        "Torrents": {"enable_torrents": "True", "enable_torrent_search": "True"},
        "Torznab": {"enable_torznab": "True"},
    }
    for section, values in want.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for key, value in values.items():
            cfg.set(section, key, value)
    with open(INI, "w") as f:
        cfg.write(f)
    os.chmod(INI, 0o600)
    print("config.ini updated:", ", ".join(f"{s}({len(v)})" for s, v in want.items()), "(values not shown)")


if __name__ == "__main__":
    main()
