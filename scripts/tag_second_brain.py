#!/usr/bin/env python3
"""
One-time (or repeatable) backfill: tags every existing point in the
second_brain Qdrant collection with a bounded, documented vocabulary
(see docs/architecture/tagging.md) so search/recall/journal generation
can filter by what actually matters instead of everything at once.

Two passes:
  1. Rule-based, for doc-seeded content (docs/ and the Obsidian vault) --
     deterministic mapping from source path to domain + topic tags, no
     LLM needed, fast.
  2. LLM-based, for Discord-originated content (facts/conversations/
     photos/journal entries) -- content is too open-ended for a lookup
     table, so one batched Ollama call tags everything in a single pass
     rather than one call per point (which would take much longer on
     this CPU-only hardware).

Usage:
    python3 scripts/tag_second_brain.py
"""
import json
import urllib.request

QDRANT_URL = "http://192.168.178.69:6333"
OLLAMA_URL = "http://192.168.178.69:11434"
COLLECTION = "second_brain"
MODEL = "qwen2.5:7b-instruct"

TOPIC_TAGS = [
    "media", "automation", "ai", "networking", "productivity", "dashboard",
    "ops", "second-brain-system", "identity", "dates", "health", "work",
    "preferences", "habits", "memory", "journal", "tasks", "credentials",
]

# source-path prefix -> (domain, [topic tags])
DOC_RULES = [
    ("docs/architecture/automation.md", ("homelab", ["automation", "second-brain-system"])),
    ("docs/architecture/journaling.md", ("homelab", ["second-brain-system", "journal"])),
    ("docs/architecture/known-issues.md", ("homelab", ["ops", "second-brain-system"])),
    ("docs/architecture/overview.md", ("homelab", [])),
    ("docs/architecture/second-brain.md", ("homelab", ["second-brain-system"])),
    ("docs/architecture/troubleshooting-second-brain.md", ("homelab", ["second-brain-system", "ops"])),
    ("docs/containers/audiobookshelf.md", ("homelab", ["media"])),
    ("docs/containers/brain-bot.md", ("homelab", ["second-brain-system"])),
    ("docs/containers/homepage.md", ("homelab", ["dashboard"])),
    ("docs/containers/huntarr.md", ("homelab", ["media"])),
    ("docs/containers/lazylibrarian.md", ("homelab", ["media"])),
    ("docs/containers/n8n.md", ("homelab", ["automation", "second-brain-system"])),
    ("docs/containers/nginx-proxy-manager.md", ("homelab", ["networking"])),
    ("docs/containers/ollama.md", ("homelab", ["second-brain-system", "ai"])),
    ("docs/containers/overseerr.md", ("homelab", ["media"])),
    ("docs/containers/prowlarr.md", ("homelab", ["media"])),
    ("docs/containers/qbittorrent.md", ("homelab", ["media"])),
    ("docs/containers/qdrant.md", ("homelab", ["second-brain-system", "ai"])),
    ("docs/containers/radarr-4k.md", ("homelab", ["media"])),
    ("docs/containers/radarr.md", ("homelab", ["media"])),
    ("docs/containers/sonarr-4k.md", ("homelab", ["media"])),
    ("docs/containers/sonarr.md", ("homelab", ["media"])),
    ("docs/containers/tautulli.md", ("homelab", ["media"])),
    ("docs/containers/trilium.md", ("homelab", ["productivity"])),
    ("docs/containers/unpackerr.md", ("homelab", ["media"])),
    ("docs/containers/vikunja.md", ("homelab", ["productivity"])),
    ("docs/containers/whisper.md", ("homelab", ["second-brain-system", "ai"])),
    ("docs/containers/infisical.md", ("homelab", ["ops", "credentials"])),
    ("docs/architecture/secrets-and-rotation.md", ("homelab", ["ops", "credentials"])),
    ("docs/architecture/stack-review-2026-08-26.md", ("homelab", ["ops"])),
    ("docs/containers/uptime-kuma.md", ("homelab", ["ops"])),
    ("docs/containers/watchtower.md", ("homelab", ["ops"])),
    ("docs/templates/container.md", ("homelab", [])),
    ("docs/README.md", ("homelab", [])),
    ("docs/second-brain-guide.md", ("homelab", ["second-brain-system"])),
    ("docs/architecture/tagging.md", ("homelab", ["second-brain-system"])),
    ("KodyBrain/daily/", ("obsidian", ["journal"])),
    ("KodyBrain/USER.md", ("obsidian", ["identity"])),
    ("KodyBrain/MEMORY.md", ("obsidian", ["memory"])),
    ("KodyBrain/SOUL.md", ("obsidian", ["identity"])),
    ("KodyBrain/HEARTBEAT.md", ("obsidian", [])),
    ("KodyBrain/HABITS.md", ("obsidian", ["habits"])),
]


def qdrant_scroll_all():
    points, offset = [], None
    while True:
        body = {"limit": 200, "with_payload": True}
        if offset is not None:
            body["offset"] = offset
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)["result"]
        points.extend(result["points"])
        offset = result["next_page_offset"]
        if offset is None:
            break
    return points


def qdrant_set_payload(point_ids, payload):
    body = {"points": point_ids, "payload": payload}
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/payload",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def rule_for_source(source):
    # Obsidian sources are absolute paths (e.g. /Users/x/Obsidian/KodyBrain/...),
    # docs/ sources are repo-relative -- substring match handles both.
    for prefix, rule in DOC_RULES:
        if prefix in source:
            return rule
    return None


def llm_tag_batch(items):
    """items: list of (id, text). Returns {id: [tags]}."""
    numbered = "\n".join(f"{i}: {text[:200]}" for i, (_id, text) in enumerate(items))
    valid = ", ".join(TOPIC_TAGS)
    prompt = (
        "You are tagging entries in a personal memory system. For each numbered entry below, "
        "assign a domain (\"personal\" for real facts/conversations about the user, or \"test\" if "
        f"the content is clearly development/testing artifacts - phrases like \"test\", \"self-test\", "
        f"\"robustness\", \"fast path test\", \"marker\", made-up placeholder facts) and 0-3 topic tags "
        f"from this exact list only: {valid}.\n\n"
        "Respond with ONLY a JSON array, one object per entry, in order: "
        '[{"domain":"personal","tags":["dates"]}, ...]\n\n'
        f"Entries:\n{numbered}\n\nJSON array:"
    )
    body = {"model": MODEL, "format": "json", "stream": False, "prompt": prompt}
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = json.load(resp)["response"]
    parsed = json.loads(raw)
    # format:"json" mode occasionally returns an object keyed by index
    # instead of a bare array -- normalize both shapes.
    if isinstance(parsed, dict):
        parsed = [parsed[k] for k in sorted(parsed.keys(), key=lambda x: int(x) if str(x).isdigit() else 0)]
    result = {}
    for (pid, _text), entry in zip(items, parsed):
        if not isinstance(entry, dict):
            result[pid] = ("personal", [])
            continue
        tags = [t for t in entry.get("tags", []) if t in TOPIC_TAGS][:3]
        domain = entry.get("domain") if entry.get("domain") in ("personal", "test") else "personal"
        result[pid] = (domain, tags)
    # Any items the model dropped (array shorter than requested) still get a default.
    for pid, _text in items:
        result.setdefault(pid, ("personal", []))
    return result


def main():
    points = qdrant_scroll_all()
    print(f"Loaded {len(points)} points")

    doc_tagged, llm_batch, skipped = 0, [], 0
    by_rule = {}
    for p in points:
        pl = p["payload"]
        source = pl.get("source")
        # Discord-originated points (type set) go to the LLM pass even if they
        # carry a source like "discord" -- that's not a doc file path.
        # Skip ones already tagged (idempotent re-run, avoids redundant LLM calls).
        if pl.get("type") in ("fact", "conversation", "photo", "journal", "apple_health", "conversation_summary"):
            if not pl.get("domain"):
                llm_batch.append((p["id"], pl.get("text", "")))
        elif source:
            rule = rule_for_source(source)
            if rule:
                domain, tags = rule
                key = (domain, tuple(tags))
                by_rule.setdefault(key, []).append(p["id"])
                doc_tagged += 1
            else:
                skipped += 1
        else:
            skipped += 1

    for (domain, tags), ids in by_rule.items():
        qdrant_set_payload(ids, {"domain": domain, "tags": list(tags)})
        print(f"  {domain} {list(tags)} -> {len(ids)} points")

    if llm_batch:
        # Small batches: output tokens (not call count) dominate wall-clock
        # time on this CPU-only hardware, so keep each call's expected
        # output short and apply results as each batch finishes -- a later
        # batch failing shouldn't lose earlier progress.
        BATCH_SIZE = 5
        total_tagged = 0
        for i in range(0, len(llm_batch), BATCH_SIZE):
            chunk = llm_batch[i:i + BATCH_SIZE]
            print(f"Tagging items {i+1}-{i+len(chunk)} of {len(llm_batch)} via LLM...")
            tagged = llm_tag_batch(chunk)
            for pid, (domain, tags) in tagged.items():
                qdrant_set_payload([pid], {"domain": domain, "tags": tags})
            total_tagged += len(tagged)
            print(f"  done ({total_tagged}/{len(llm_batch)} so far)")

    print(f"Done. doc-tagged={doc_tagged} llm-tagged={len(llm_batch)} skipped(untagged)={skipped}")


if __name__ == "__main__":
    main()
