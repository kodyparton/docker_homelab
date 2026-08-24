# Whisper

Speech-to-text service — transcribes Discord voice messages so they flow into the second brain's normal text pipeline. Local, no external API.

## Quick Facts

| | |
|---|---|
| **Image** | `onerahmet/openai-whisper-asr-webservice:latest` (faster-whisper engine) |
| **Container name** | `whisper` |
| **Compose file** | `whisper/compose.yml` |
| **Host** | Mac Mini (`192.168.178.69`) |
| **Port(s)** | `9000:9000` |
| **Local URL** | `http://192.168.178.69:9000` (interactive API docs at `/docs`) |
| **Public URL** | none (LAN only) |
| **PUID/PGID** | n/a |
| **Timezone** | `America/Chicago` |
| **Restart policy** | `unless-stopped` |
| **Model** | `base` (74M params) — chosen for speed over accuracy given this is CPU inference alongside an already-loaded 7B chat model; upgrade to `small`/`medium` via the `ASR_MODEL` env var if transcription quality isn't good enough, at the cost of slower responses |

## Volumes / Mounts

| Host path | Container path | Purpose | Notes |
|---|---|---|---|
| `whisper/config` | `/root/.cache` | downloaded model weights | gitignored |

## Dependencies

- **Depends on:** nothing.
- **Depended on by:** `brain-bot` — any Discord message with an audio attachment gets downloaded and POSTed here for transcription before being forwarded to n8n as if it were typed text.

## Credentials & Secrets

None — no auth by default, LAN-only for that reason (same posture as Ollama/Qdrant).

## External Access

Not exposed via NPM — LAN-only, intentionally.

## Backups

n/a — stateless, models are re-downloadable.

## Automation

Not called from n8n directly — `brain-bot` calls it before ever reaching n8n, so a voice message and a typed message look identical by the time workflow 18 sees them.

## Known Issues / Gotchas

- **Verified live** (2026-08-24) with a synthesized test clip ("remember that the garage code is one two three four" → transcribed correctly as "Remember that the garage code is 1234.") — accuracy on a real human voice, accents, or background noise is untested.
- If transcription fails (service down, bad audio format), `brain-bot` tells you in Discord rather than silently dropping the voice message — check `docker logs whisper` and `docker logs brain-bot`.
- CPU-only inference — a longer voice message will take proportionally longer to transcribe, adding to the overall reply latency on top of the classification + generation calls that follow.

## Change Log

- `2026-08-24` — Deployed, integrated into `brain-bot`.
