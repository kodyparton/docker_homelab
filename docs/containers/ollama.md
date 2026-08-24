# Ollama

Local LLM runtime — powers the second brain's chat generation and text embeddings, entirely on-box (no external API, no per-request cost).

## Quick Facts

| | |
|---|---|
| **Image** | `ollama/ollama:latest` |
| **Container name** | `ollama` |
| **Compose file** | `ollama/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `11434:11434` |
| **Local URL** | `http://192.168.178.69:11434` |
| **Public URL** | none (LAN only — this should never be exposed publicly) |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `ollama/config` | `/root/.ollama` | downloaded models | gitignored — models are multi-GB, never belong in git |

## Models Installed

| Model | Size | Purpose |
|---|---|---|
| `qwen2.5:7b-instruct` | 4.7 GB | Chat generation for the second brain |
| `nomic-embed-text` | 274 MB | Text embeddings (768-dim) for Qdrant |

Chosen for this hardware (Apple M1, OrbStack VM capped around 7.8GB RAM): `qwen2.5:7b-instruct` at default (Q4_K_M) quantization is one of the best quality/size tradeoffs available for local inference at this RAM budget. If response quality isn't good enough, a bigger model can be pulled (`docker exec ollama ollama pull <model>`) and the model name changed in workflow 18's two Ollama HTTP Request nodes — but check available disk/RAM first (the host was at 100% disk capacity once already this session; `docker image prune -a` reclaims unused image layers if needed).

## Dependencies

- **Depends on:** nothing.
- **Depended on by:** n8n workflow 18 (Second Brain - Chat) for both embedding and generation calls.

## Credentials & Secrets

None — Ollama has no auth by default. It's LAN-only for that reason; do not add a public NPM proxy host for this without adding authentication in front of it.

## External Access

Not exposed via NPM — LAN-only, intentionally.

## Backups

Not covered by `scripts/backup_check.sh`. Models are re-downloadable (not unique data) so low priority; if custom fine-tunes or Modelfiles are ever added, reconsider.

## Automation

- **18 - Second Brain - Chat** — every message calls Ollama twice (once to embed, once to generate).
- `scripts/seed_second_brain.py` also calls Ollama's embeddings endpoint directly when bulk-loading knowledge.

## Known Issues / Gotchas

- **Disk space is tight on this host.** Pulling `qwen2.5:7b-instruct` (4.7GB) failed once with "no space left on device" until 22GB of unused Docker images were pruned. Check `df -h` before pulling additional/larger models.
- Cold-start inference (first request after container start, or first request for a model not yet loaded into memory) is noticeably slower than subsequent requests — Ollama keeps recently-used models warm in memory for a few minutes by default.
- No conversation memory between messages — each Discord message is a fresh, independent RAG query against Qdrant. There's no multi-turn context window today; see `docs/architecture/second-brain.md` for what that would take to add.

## Change Log

- `2026-08-24` — Deployed with `qwen2.5:7b-instruct` and `nomic-embed-text`.
