#!/usr/bin/env python3
"""
Push a workflow JSON file (as produced by export_n8n_workflows.py) back to
n8n via its API. Companion to export_n8n_workflows.py - export is the
backup/diff direction, this is the deploy direction.

Usage:
    python3 scripts/deploy_n8n_workflow.py n8n/workflows/18-second-brain-chat.json

Reads the workflow's id from the file itself. Only sends the fields n8n's
PUT /workflows/{id} actually accepts (name, nodes, connections, settings) -
sending read-only fields like id/active/tags/versionId back causes a 400.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = REPO_ROOT / "scripts" / ".n8n_api_key"
BASE_URL = "http://localhost:5678/api/v1"

UPDATABLE_FIELDS = ("name", "nodes", "connections", "settings")


def main():
    if len(sys.argv) != 2:
        print("usage: deploy_n8n_workflow.py <path-to-workflow.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    full = json.loads(path.read_text())
    workflow_id = full["id"]
    body = {k: full[k] for k in UPDATABLE_FIELDS if k in full}
    if "settings" not in body:
        body["settings"] = {}

    key = KEY_FILE.read_text().strip()
    req = urllib.request.Request(
        f"{BASE_URL}/workflows/{workflow_id}",
        data=json.dumps(body).encode(),
        headers={"X-N8N-API-KEY": key, "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
            print(f"Deployed: {result['name']} (id {result['id']})")
    except urllib.error.HTTPError as e:
        print(f"FAILED [{e.code}]: {e.read().decode()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
