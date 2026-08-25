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
- **No GPU passthrough to Docker containers on macOS.** Confirmed via Ollama's own startup log (`msg="inference compute" id=cpu library=cpu`) — inference is CPU-only regardless of the M1's GPU cores. This makes it genuinely slow: ~35-40s for even a short classify call, ~60-100s for a full generated answer. `OLLAMA_KEEP_ALIVE=60m` is set specifically to avoid paying an additional ~25s model-reload penalty on top of that whenever the model's been idle. Every workflow that calls Ollama needs a generous timeout (90-180s) to account for this — a too-short timeout here was the direct cause of a real "second brain isn't working" bug on 2026-08-25 (see `known-issues.md`).
- Cold-start inference (first request after container start, or first request for a model not yet loaded into memory) is noticeably slower than subsequent requests, on top of the above.
- **Can get OOM-killed under load** (`llama-server process has terminated: signal: killed` in `docker logs ollama`) if the host doesn't have enough memory headroom — this genuinely happened on 2026-08-25 when OrbStack's VM was capped at 8GB. Fixed by giving the VM more memory (`orb config set memory_mib 12288`, see the host-level note below) rather than anything Ollama-side; if it recurs, check `docker stats ollama` for memory pressure before assuming it's a workflow bug.
- **Keep prompts small.** Dumping a large dataset (e.g. an entire media library) into a prompt to answer a narrow question makes even simple queries take minutes on this hardware and risks hitting node-level timeouts. Filter/summarize data in a Code node before it ever reaches the prompt — see how `18 - Second Brain - Chat`'s `media_query` intent does this (fuzzy-matches to ~5 relevant items instead of sending the whole library).

## Host-level dependency

This container's reliability depends on OrbStack's VM having enough memory, which is a **host-level setting, not a Docker Compose setting** — `orb config set memory_mib <value>` then `orb stop && orb start` (restarts every container on this host, they all come back via `restart:unless-stopped`). Currently set to 12288 (12GB) out of this Mac's 16GB total.

## Change Log

- `2026-08-24` — Deployed with `qwen2.5:7b-instruct` and `nomic-embed-text`.
- `2026-08-25` — Set `OLLAMA_KEEP_ALIVE=60m` and increased calling workflows' timeouts after root-causing a real failure to CPU-only inference speed. Separately, root-caused and fixed real OOM-kills by increasing OrbStack's VM memory from 8GB to 12GB.
