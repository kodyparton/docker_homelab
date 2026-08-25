#!/usr/bin/env python3
"""
Back up every n8n workflow to git as JSON, so workflow logic isn't only
ever living inside n8n's own database (which has already been silently
reverted by a stale browser tab once).

Usage:
    python3 scripts/export_n8n_workflows.py

Reads the n8n API key from scripts/.n8n_api_key (gitignored — the key
itself is a credential, this script and its output are not). Writes
one file per workflow to n8n/workflows/<id>.json, pretty-printed and
with volatile fields (execution stats, timestamps) stripped so diffs
in git reflect real logic changes, not noise. This is a backup/diff
aid, not a deploy mechanism — to restore a workflow, PUT its JSON back
via the n8n API (see docs/architecture/second-brain.md for the pattern
used throughout this repo's history).
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = REPO_ROOT / "scripts" / ".n8n_api_key"
OUT_DIR = REPO_ROOT / "n8n" / "workflows"
BASE_URL = "http://localhost:5678/api/v1"

# Fields that change on every save/run but don't reflect a real logic
# change - stripped so git diffs stay meaningful.
VOLATILE_FIELDS = ("updatedAt", "createdAt", "versionId", "versionCounter", "shared", "triggerCount")


def api_get(path):
    key = KEY_FILE.read_text().strip()
    req = urllib.request.Request(f"{BASE_URL}{path}", headers={"X-N8N-API-KEY": key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    if not KEY_FILE.exists():
        print(f"No API key found at {KEY_FILE} - see docs/architecture/second-brain.md for how to create one.")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = api_get("/workflows")
    workflows = data["data"]

    exported = []
    for summary in workflows:
        full = api_get(f"/workflows/{summary['id']}")
        for f in VOLATILE_FIELDS:
            full.pop(f, None)
        slug = slugify(full["name"])
        path = OUT_DIR / f"{slug}.json"
        path.write_text(json.dumps(full, indent=2, sort_keys=True) + "\n")
        exported.append(slug)
        print(f"  {full['name']} -> {path.relative_to(REPO_ROOT)}")

    # Remove stale exports for workflows that no longer exist
    existing_slugs = {slugify(w["name"]) for w in workflows}
    for f in OUT_DIR.glob("*.json"):
        if f.stem not in existing_slugs:
            f.unlink()
            print(f"  removed stale export: {f.relative_to(REPO_ROOT)}")

    print(f"Exported {len(exported)} workflows to {OUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
