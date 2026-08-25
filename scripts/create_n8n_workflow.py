#!/usr/bin/env python3
"""
Create a brand-new workflow in n8n from a JSON file (name/nodes/connections/
settings only - no id yet). Prints the assigned id so it can be referenced
elsewhere, then writes the full workflow (as returned by n8n, matching the
shape export_n8n_workflows.py produces) into n8n/workflows/.

Usage:
    python3 scripts/create_n8n_workflow.py /path/to/new_workflow.json
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = REPO_ROOT / "scripts" / ".n8n_api_key"
OUT_DIR = REPO_ROOT / "n8n" / "workflows"
BASE_URL = "http://localhost:5678/api/v1"


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    if len(sys.argv) != 2:
        print("usage: create_n8n_workflow.py <path-to-workflow.json>")
        sys.exit(1)

    body = json.loads(Path(sys.argv[1]).read_text())
    key = KEY_FILE.read_text().strip()
    req = urllib.request.Request(
        f"{BASE_URL}/workflows",
        data=json.dumps(body).encode(),
        headers={"X-N8N-API-KEY": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"FAILED [{e.code}]: {e.read().decode()}")
        sys.exit(1)

    print(f"Created: {result['name']} (id {result['id']})")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(result["name"])
    path = OUT_DIR / f"{slug}.json"
    for f in ("updatedAt", "createdAt", "versionId", "versionCounter", "shared", "triggerCount"):
        result.pop(f, None)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"  saved -> {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
