# Trilium

Personal note-taking app (hierarchical notes, not part of the second-brain Obsidian vault — a separate, unrelated notes tool).

## Quick Facts

| | |
|---|---|
| **Image** | `triliumnext/trilium:latest` |
| **Container name** | `trilium-trilium-1` (no explicit `container_name`) |
| **Compose file** | `trilium/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `8080:8080` |
| **Local URL** | `http://192.168.178.69:8080` |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `trilium/data` | `/home/node/trilium-data` | notes database | gitignored |

## Dependencies

- **Depends on:** nothing.
- **Depended on by:** Homepage (status widget).

## Credentials & Secrets

None referenced elsewhere — first-run setup happens in its own web UI.

## External Access

Not exposed via NPM — LAN-only.

## Backups

Not currently covered by `scripts/backup_check.sh`.

## Automation

- **02 - Docker Drift Detection**

## Known Issues / Gotchas

- **Never started successfully until 2026-08-17.** Two bugs stacked: (1) it bind-mounted `/etc/timezone` and `/etc/localtime` from the host, which don't exist in the expected form under OrbStack's VM (`mount src=/etc/timezone ... not a directory`), blocking startup entirely; (2) its data volume defaulted to `~/trilium-data` (empty, unused) rather than the repo's own `trilium/data` folder. Fixed by removing the two host TZ bind mounts (replaced with a `TZ` env var, which Trilium respects natively) and pointing the volume at `./data`.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Fixed startup failure (bad host TZ bind mounts) and wrong data volume path.
