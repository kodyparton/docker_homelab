# Troubleshooting: "The second brain isn't responding"

A runbook for when Discord messages to the brain bot get no reply, an error reply, or take an unreasonably long time. Work through this top to bottom — most failures are caught by the first two or three checks.

## 1. Is everything actually running?

```
docker ps --format '{{.Names}}: {{.Status}}'
```

Check `ollama`, `qdrant`, `whisper`, `brain-bot`, `n8n-n8n-1`. Anything not `Up`, restart it:

```
docker compose -f <service>/compose.yml up -d
```

Workflow 27 (Second Brain Health Monitor) checks this automatically every 15 minutes and posts to Discord if something's down — check that channel first, it may have already told you.

## 2. Is workflow 18 actually active?

n8n workflows are created inactive by default and the API can't activate them, so this gets missed after any redeploy. In n8n's UI, open **18 - Second Brain - Chat** and confirm the toggle in the top right is on. If it's off, every message to the bot silently 404s at the webhook.

## 3. Is Ollama actually the bottleneck (it usually is)?

This entire stack runs LLM inference on CPU only — there is no GPU passthrough to Docker on this Mac (confirmed via `docker logs ollama` showing `inference compute id=cpu`). Every message to the brain does at least one Ollama call (classify intent), and most intents do a second one (generate the actual reply). Expect **replies to take one to several minutes**, not seconds — this is normal, not a bug. See "Known slowness, not a bug" below before assuming something's broken.

Check what Ollama is doing right now:

```
curl -s http://localhost:11434/api/ps | python3 -m json.tool
docker exec ollama ps aux | grep llama-server
```

- If nothing is loaded and no request is in flight, Ollama is idle — the delay is elsewhere (n8n, brain-bot, Discord).
- If a `llama-server` process is pegged near 600%+ CPU, it's actively working through a real request. Let it finish rather than restarting mid-request — restarting loses that request's classify pass and the user just sees a dropped/failed reply.
- If `docker logs ollama --tail 50` shows `llama-server process has terminated: signal: killed`, it was OOM-killed. Check `orb config` (see below) — this happened once before when OrbStack's VM memory cap was set below what the running containers actually needed.

## 4. Check for an OOM kill / OrbStack memory cap

```
orb config
```

The VM's `memory_mib` is a host-level setting, not per-container — it caps everything Docker-related on this Mac at once. It's currently set to 12288 (12GB) of the Mac's 16GB. If you need to raise it:

```
orb config set memory_mib <new value>
orb stop && orb start
```

This restarts every container (they all have `restart: unless-stopped` so they come back on their own — give it a minute).

## 5. Check disk space

Ollama model pulls and Qdrant writes both fail ungracefully when the disk is nearly full. This host runs tight on space as a matter of course:

```
df -h /
```

Below ~5GB free, expect weirdness. `docker image prune -a` reclaims space from unused images (rarely much, everything here tends to be in active use) — the real fix is usually just clearing old downloads/media elsewhere on the host.

## 6. Check n8n's execution log for the failing run

The n8n public API can't read execution history (confirmed 403 on `/executions`), so this has to be done in the n8n UI: open the workflow, click **Executions** in the left sidebar, find the failed/hung run, and open it to see exactly which node failed and why. This is the single most useful thing to check for anything that isn't covered above — most of the real bugs found during this project (a Switch node's fallback routing silently doing nothing, an HTTP node splitting array responses into separate items, a missing entry in an intent whitelist) were only findable this way.

## 7. Run the self-test workflow

**28 - Second Brain Self-Test** runs daily at 05:00 and fires six canned messages through the six intents that are safe to test automatically (`chat`, `question`, `store`/`forget` as a self-cleaning pair, `list_tasks`, `media_query`) — it posts a pass/fail summary to Discord only when something fails. You can also run it on demand from n8n's UI ("Execute Workflow") to check the whole pipeline right now instead of waiting for the schedule.

It deliberately does **not** test `task`, `complete_task`, or `note` — those create/modify real data in Vikunja and Trilium, and a daily automated test firing them would pollute your actual task list and notes. If you suspect one of those three specifically is broken, test it manually with a message you don't mind being real ("remind me to test the second brain" is a fine, harmless real task).

## 8. Check brain-bot's own logs

If Discord shows nothing at all (not even an error), the problem is likely upstream of n8n entirely:

```
docker logs brain-bot --tail 50
```

Common causes here: the bot's Discord token expired/was regenerated, `DISCORD_CHANNEL_IDS` doesn't include the channel you're messaging in, or the `N8N_WEBHOOK_URL` in `brain-bot/.env` points at the wrong host/path.

## Known slowness, not a bug

Every message does at least a classify pass; most do a second generate pass. On this Mac Mini's CPU, a single call against the `qwen2.5:7b-instruct` model has been observed anywhere from ~35 seconds (idle, warm) to several minutes (under any concurrent load, including this project's own testing). If a reply comes back — even a slow one — the system is working correctly. If you want it meaningfully faster, that requires either better hardware (a GPU-capable box, or Apple Silicon inference with GPU passthrough once OrbStack/Docker Desktop support it) or a smaller model — **a smaller model was already tried and measured no faster** on this hardware (`qwen2.5:1.5b-instruct`, tested and removed — see `known-issues.md`), so that's a dead end unless a different, genuinely lighter-weight local model is tried.
