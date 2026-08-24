# Watchtower

Watches every other container's image for updates and auto-recreates them when a newer image is available.

## Quick Facts

| | |
|---|---|
| **Image** | `nickfedor/watchtower:latest` |
| **Container name** | `watchtower` |
| **Compose file** | `watchtower/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | none (no web UI) |
| **Local URL** | n/a |
| **Public URL** | n/a |
| **PUID/PGID** | n/a |
| **Timezone** | container default (no `TZ` set) |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `/var/run/docker.sock` | `/var/run/docker.sock` | needs full Docker socket access to inspect/recreate every container | read-write, required for its function |

## Dependencies

- **Depends on:** the Docker daemon directly (via socket).
- **Depended on by:** every other container, indirectly (it's what keeps images current).

## Credentials & Secrets

None.

## External Access

n/a.

## Backups

n/a — stateless.

## Automation

- **02 - Docker Drift Detection** — indirectly relevant: since Watchtower changes running image digests out from under `compose.yml`'s pinned tags, drift detection may flag a service as "drifted" right after Watchtower updates it. That's expected, not a bug — it just means the compose file's `:latest` tag and the actually-running image genuinely diverged in digest, which drift detection is correctly designed to catch either way.

## Known Issues / Gotchas

- **Image was frozen at a 2023-11 build (fixed 2026-08-17):** the original `containrrr/watchtower:latest` image was from an abandoned project fork — its bundled Docker client only spoke API v1.25, while the OrbStack daemon requires ≥v1.40, so it crash-looped indefinitely (`RestartCount` over 10,000 by the time this was found). Switched to `nickfedor/watchtower`, the actively maintained community successor. If this ever crash-loops again, check the image's actual build date first (`docker image inspect nickfedor/watchtower:latest --format '{{.Created}}'`) before assuming it's a config problem.

## Change Log

- `2026-08-24` — Doc created.
- `2026-08-17` — Switched from abandoned `containrrr/watchtower` to `nickfedor/watchtower` after finding it crash-looping on a stale 2023 image.
