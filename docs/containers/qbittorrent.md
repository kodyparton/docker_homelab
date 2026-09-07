# qBittorrent

Torrent download client — receives grabs from Sonarr/Radarr (all 4 instances) and Prowlarr, downloads to the shared `/mnt/downloads` share where the *arr apps pick finished files up for import.

## Quick Facts

| | |
|---|---|
| **Image** | `lscr.io/linuxserver/qbittorrent:latest` |
| **Container name** | `qbittorrent` |
| **Compose file** | `qbittorrent/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) — **`network_mode: host`**, not bridged |
| **Port(s)** | WebUI `30024` (via `WEBUI_PORT` env, no `ports:` mapping needed under host networking), torrenting `50415` |
| **Local URL** | `http://192.168.178.69:30024` |
| **Public URL** | `https://downloads.kodyparton.com` (via NPM) — **currently misrouted, see Known Issues** |
| **PUID/PGID** | `1000/1000` |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `always` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `qbittorrent/config` | `/config` | app config, session state, GeoDB | gitignored |
| `/Volumes/downloads` | `/mnt/downloads` | download destination, shared with all 4 *arr apps | SMB share — see known issue |

## Dependencies

- **Depends on:** nothing internal.
- **Depended on by:** Sonarr, Sonarr 4K, Radarr, Radarr 4K (download client), Unpackerr (extracts archives from here), Homepage (status widget).

## Credentials & Secrets

WebUI login: username `kparton`, password is a PBKDF2 hash on disk (`qBittorrent.conf`) — **cannot be recovered**, only reset via the WebUI or config. Needed (and currently still placeholder) in:
- Homepage's `.env` (`HOMEPAGE_VAR_QBITTORRENT_PASSWORD`)
- n8n workflow 14's "qBittorrent Login" node

## External Access

NPM proxy host `downloads.kodyparton.com` forwards to `192.168.178.69:30024` — fixed 2026-08-27 (was pointed at a dead host `10.10.0.130`, same class of stale-migration issue n8n had).

## Backups

Not covered by workflow 03 — qBittorrent has no "backup" in the traditional sense, its `BT_backup/` directory is live torrent session/resume state, not a discrete backup artifact, so it's deliberately excluded from backup verification.

## Automation

- **02 - Docker Drift Detection**
- **09 - Mount Health Self-Healer** — inactive (found 2026-08-29, was never actually turned on) and now moot regardless: `/mnt/downloads` is a native CIFS volume as of 2026-08-29, not a host-passthrough mount, so the ENOENT-drop failure mode this workflow existed for can no longer happen here.
- **14 - Weekly Media Server Digest** — pulls weekly upload/download totals (pending real password)
- Unpackerr polls this instance to extract completed downloads.

## Known Issues / Gotchas

- ~~Same SMB-passthrough mount fragility as the *arr apps~~ — resolved 2026-08-29. `/mnt/downloads` is now a native Linux CIFS volume (`nas_downloads`), mounted directly by Docker inside OrbStack's VM, no macOS host passthrough involved. See `docs/architecture/known-issues.md`.
- Runs under `network_mode: host`, not the usual bridge network — this is intentional for torrenting port forwarding, but means it doesn't appear on any docker-compose project network and can't be reached by container name from other containers, only via the host's LAN IP.

## Change Log

- `2026-08-24` — Doc created.
