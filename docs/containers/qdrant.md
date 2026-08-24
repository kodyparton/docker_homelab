# Qdrant

Vector database — the second brain's actual long-term memory. Every fact it knows lives here as a text chunk + embedding, retrieved by semantic similarity rather than keyword search.

## Quick Facts

| | |
|---|---|
| **Image** | `qdrant/qdrant:latest` |
| **Container name** | `qdrant` |
| **Compose file** | `qdrant/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `6333:6333` |
| **Local URL** | `http://192.168.178.69:6333` (dashboard at `/dashboard`) |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `qdrant/storage` | `/qdrant/storage` | all vector/point data | gitignored — this is the actual memory content, real and potentially personal |

## Collections

| Collection | Vector size | Distance metric | Contents |
|---|---|---|---|
| `second_brain` | 768 (matches `nomic-embed-text`) | Cosine | Every fact learned via Discord ("remember: ...") plus the initial seed from `docs/` via `scripts/seed_second_brain.py` |

## Dependencies

- **Depends on:** nothing.
- **Depended on by:** n8n workflow 18 (both the ingest and query branches), `scripts/seed_second_brain.py`.

## Credentials & Secrets

None — no auth by default. LAN-only for that reason, same as Ollama.

## External Access

Not exposed via NPM — LAN-only, intentionally.

## Backups

**Not yet covered by `scripts/backup_check.sh` — this is the highest-priority gap in backup coverage in the whole stack**, since `qdrant/storage` is the only copy of everything the second brain has been taught. Worth adding a scheduled `docker exec qdrant` snapshot (Qdrant has a built-in snapshot API: `POST /collections/second_brain/snapshots`) to the backup verification workflow.

## Automation

- **18 - Second Brain - Chat** — upserts new facts, searches on every question.

## Known Issues / Gotchas

- No dedup by content — re-seeding the same file twice with `scripts/seed_second_brain.py` is safe (uses a content hash for point IDs), but two *different* phrasings of the same fact will both get stored and both surface in search results. Not a functional bug, just something to be aware of if answers start looking redundant.
- `score_threshold: 0.5` is set in workflow 18's search call to avoid surfacing totally irrelevant memories as false context — if the brain seems to be "forgetting" things that were definitely stored, that threshold may be too strict for how `nomic-embed-text` scores certain phrasings; check via the Qdrant dashboard (`http://192.168.178.69:6333/dashboard`) before assuming data loss.

## Change Log

- `2026-08-24` — Deployed. Created the `second_brain` collection. Seeded with the initial homelab documentation via `scripts/seed_second_brain.py`.
