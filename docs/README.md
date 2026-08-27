# Homelab Documentation

Documentation for the `docker_homelab` stack — a Mac Mini running ~29 self-hosted services under Docker Compose (via OrbStack), automated by n8n.

## Start here

- **[Second Brain User Guide](second-brain-guide.md)** — start here if you just want to know how to use it day to day.
- **[Architecture Overview](architecture/overview.md)** — service dependency map, port map, domain/reverse-proxy map, data flow.
- **[Automation Map](architecture/automation.md)** — every n8n workflow, what it touches, what it's allowed to change automatically.
- **[Second Brain (technical)](architecture/second-brain.md)** — how the second brain is built: architecture, internals, setup steps.
- **[Daily Journaling](architecture/journaling.md)** — evening prompts, automatic daily journal generation from conversations/photos/Strava/Apple Health, setup steps.
- **[Single Sign-On](architecture/sso.md)** — Authelia OIDC setup, what's still blocked on DNS, and why Vaultwarden keeps local login.
- **[Known Issues](architecture/known-issues.md)** — open problems and their status, resolved-issue changelog.

## Per-service docs

One file per running container in [`containers/`](containers/), each following the same [template](templates/container.md): quick facts, volumes, dependencies, credentials, external access, backups, related automation, known gotchas, and a change log.

| Service | Doc |
|---|---|
| Sonarr | [containers/sonarr.md](containers/sonarr.md) |
| Sonarr 4K | [containers/sonarr-4k.md](containers/sonarr-4k.md) |
| Radarr | [containers/radarr.md](containers/radarr.md) |
| Radarr 4K | [containers/radarr-4k.md](containers/radarr-4k.md) |
| Prowlarr | [containers/prowlarr.md](containers/prowlarr.md) |
| qBittorrent | [containers/qbittorrent.md](containers/qbittorrent.md) |
| Overseerr | [containers/overseerr.md](containers/overseerr.md) |
| Tautulli | [containers/tautulli.md](containers/tautulli.md) |
| Huntarr | [containers/huntarr.md](containers/huntarr.md) |
| Audiobookshelf | [containers/audiobookshelf.md](containers/audiobookshelf.md) |
| LazyLibrarian | [containers/lazylibrarian.md](containers/lazylibrarian.md) |
| Unpackerr | [containers/unpackerr.md](containers/unpackerr.md) |
| Watchtower | [containers/watchtower.md](containers/watchtower.md) |
| n8n | [containers/n8n.md](containers/n8n.md) |
| Trilium | [containers/trilium.md](containers/trilium.md) |
| Nginx Proxy Manager | [containers/nginx-proxy-manager.md](containers/nginx-proxy-manager.md) |
| Homepage | [containers/homepage.md](containers/homepage.md) |
| Vikunja | [containers/vikunja.md](containers/vikunja.md) |
| Ollama | [containers/ollama.md](containers/ollama.md) |
| Qdrant | [containers/qdrant.md](containers/qdrant.md) |
| Brain Bot | [containers/brain-bot.md](containers/brain-bot.md) |
| Whisper | [containers/whisper.md](containers/whisper.md) |
| Infisical | [containers/infisical.md](containers/infisical.md) |
| Uptime Kuma | [containers/uptime-kuma.md](containers/uptime-kuma.md) |
| Authelia (SSO) | [containers/authelia.md](containers/authelia.md) |
| Vaultwarden | [containers/vaultwarden.md](containers/vaultwarden.md) |
| Paperless-ngx | [containers/paperless.md](containers/paperless.md) |
| Immich | [containers/immich.md](containers/immich.md) |
| AdGuard Home | [containers/adguard.md](containers/adguard.md) |

## Keeping this updated

This isn't a one-time snapshot — it's meant to track the real state of the stack. Whenever a service's `compose.yml`, ports, mounts, credentials, or automation coverage changes, its doc in `containers/` and the relevant map in `architecture/` get updated in the same pass as the change itself, with a dated entry in that doc's Change Log. New services get a new doc from the template before being considered "done."
