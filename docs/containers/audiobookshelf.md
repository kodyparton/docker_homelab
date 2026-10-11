# Audiobookshelf

Audiobook and podcast server with its own web player and mobile app support.

## Quick Facts

| | |
|---|---|
| **Image** | `ghcr.io/advplyr/audiobookshelf:latest` |
| **Container name** | `audiobookshelf` |
| **Compose file** | `audiobookshelf/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `30033:80` | host `30033` → container `80` — the app listens on `80`, not `30033` |
| **Local URL** | `http://192.168.178.69:30033` |
| **Public URL** | `https://audiobooks.kodyparton.com` (LAN-only DNS, via NPM) |
| **PUID/PGID** | n/a |
| **Timezone** | `Europe/Amsterdam` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `nas_audiobooks` (Docker CIFS volume, `//192.168.178.38/media/audiobooks`) | `/audiobooks` | audiobook library | native CIFS, `uid=0,gid=0`; see `architecture/known-issues.md` |
| `audiobookshelf/podcasts` | `/podcasts` | podcast downloads | local disk, not SMB |
| `audiobookshelf/config` | `/config` | app config, sqlite db | gitignored |
| `audiobookshelf/metadata` | `/metadata` | covers, cache, scheduled backups | gitignored |

## Dependencies

- **Depends on:** nothing internal.
- **Depended on by:** Homepage (status widget).

## Credentials & Secrets

None referenced elsewhere in this repo currently — no API key wired into any n8n workflow or Homepage widget yet.

## External Access

Proxied by NPM as `audiobooks.kodyparton.com` (added 2026-08-29, proxy host reusing the `*.kodyparton.com` wildcard cert). Resolvable only on the LAN via AdGuard Home — not published to public DNS.

## Backups

Automatic backups were **disabled by default** (`backupSchedule: false` in its settings DB) and had never run. Fixed 2026-08-17 — enabled a daily 3am schedule (`backupSchedule: "0 3 * * *"`, `backupsToKeep: 2`), edited directly in `config/absdatabase.sqlite` while the container was stopped. Verified by workflow **03 - Backup Verification** — stale threshold 14 days, checked in `metadata/backups/`.

## Automation

- **02 - Docker Drift Detection**
- **03 - Backup Verification**

## Known Issues / Gotchas

- **Its library mount is now a native Docker CIFS volume (`nas_audiobooks`), not a host SMB bind mount** — changed in the 2026-08-29 migration. That swapped one failure mode for another: the mount now fails at container *creation* when the NAS is unreachable, which no restart policy can recover (see `architecture/known-issues.md`). It happened on 2026-09-17 when the NAS changed IP, and the container stayed down ~4h. `scripts/cifs_volume_health_check.sh` covers this, but is still not installed as a launchd agent.
- The older host-passthrough concern (workflow 09's ENOENT self-healer not watching this mount) no longer applies — that mount class is gone for this container.

## Change Log

- `2026-09-27` — Doc corrected against the live container: port mapping is `30033:80` (not `30033:30033`), `TZ=Europe/Amsterdam` (not `America/Chicago`), library is the `nas_audiobooks` CIFS volume (not a `/Volumes/media/audiobooks` bind), and it *is* proxied as `audiobooks.kodyparton.com`. Verified running: server 2.36.1, `isInit: true`, HTTP 200 locally and through NPM, library readable.
- `2026-08-24` — Doc created.
- `2026-08-17` — Backups were silently disabled since setup; enabled a daily schedule.
