#!/usr/bin/env python3
"""
Read-only check: did any n8n workflow fail (error/crashed) or get stuck
(running far longer than it should) since the last check?

Built 2026-08-29 after discovering three real, independent n8n problems in
one sweep (a stale "Mac Mini SSH" credential, an unfilled weather-coordinates
placeholder, and the already-known Discord webhook placeholder) with no
mechanism watching for any of it. Deliberately does NOT go through n8n's own
API (the stored N8N_API_KEY lacks executions:read/write scope -- confirmed
2026-08-29, GET/POST/DELETE on /executions all return 403) or SSH (the
credential workflows would use for that is itself one of today's failures --
using it to monitor itself would be circular). Instead this reads n8n's
SQLite database directly via `docker cp`, the same method used to diagnose
today's failures, and alerts by email via Gmail SMTP (the one channel
confirmed working today; Discord's webhook credential is a known placeholder,
see known-issues.md).

State (which execution IDs have already been alerted on) is kept in
n8n_failure_check_state.json next to this script so re-runs don't re-alert
on the same old failures. Stuck executions (status=running past
STUCK_MINUTES) are re-alerted once per day until resolved, since they
represent an ongoing condition, not a one-time event.

Usage: python3 scripts/n8n_failure_check.py [--dry-run]
Intended to run on a schedule via cron (see crontab -l).
"""
import json
import smtplib
import subprocess
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = Path(__file__).resolve().parent / "n8n_failure_check_state.json"
STUCK_MINUTES = 20
# A workflow failing repeatedly (e.g. every 15min, a known unfixed issue)
# would otherwise generate a fresh "new" execution ID every single run --
# alert once per workflow per cooldown window, not once per execution.
WORKFLOW_ALERT_COOLDOWN_HOURS = 6
# Read from the environment (or homepage/.env, which is gitignored) rather than
# hardcoding a personal address into a public repo. Falls back to the literal
# only via env so cron keeps working -- see homepage/.env: ALERT_EMAIL.
def _alert_email():
    v = os.environ.get("ALERT_EMAIL")
    if v:
        return v
    envf = REPO_ROOT / "homepage" / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            if line.startswith("ALERT_EMAIL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


ALERT_TO = _alert_email()
ALERT_FROM = ALERT_TO
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from infisical_client import get_secret  # noqa: E402


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"alerted_execution_ids": [], "stuck_last_alerted": {}, "workflow_last_alerted": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=1))


def fetch_db():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        tmp_path = f.name
    subprocess.run(
        ["docker", "cp", "n8n-n8n-1:/home/node/.n8n/database.sqlite", tmp_path],
        check=True, capture_output=True,
    )
    return tmp_path


def get_workflow_names(conn):
    rows = conn.execute("SELECT id, name FROM workflow_entity").fetchall()
    return {wid: name for wid, name in rows}


def main():
    dry_run = "--dry-run" in sys.argv
    state = load_state()
    db_path = fetch_db()
    conn = sqlite3.connect(db_path)
    names = get_workflow_names(conn)

    since = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    failed = conn.execute(
        "SELECT id, workflowId, status, startedAt FROM execution_entity "
        "WHERE status IN ('error','crashed') AND startedAt > ? ORDER BY id",
        (since,),
    ).fetchall()

    unseen_failures = [f for f in failed if f[0] not in state["alerted_execution_ids"]]

    # Gate by per-workflow cooldown: a workflow already alerted on recently
    # gets its new execution IDs recorded as seen (so they don't pile up and
    # dump all at once when the cooldown expires) but doesn't trigger another
    # email until the cooldown passes.
    now = datetime.now(timezone.utc)
    new_failures = []
    for f in unseen_failures:
        wf_id = f[1]
        last = state["workflow_last_alerted"].get(wf_id)
        if last:
            last_dt = datetime.fromisoformat(last)
            if now - last_dt < timedelta(hours=WORKFLOW_ALERT_COOLDOWN_HOURS):
                continue
        new_failures.append(f)

    stuck_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STUCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    stuck = conn.execute(
        "SELECT id, workflowId, startedAt FROM execution_entity "
        "WHERE status = 'running' AND startedAt < ?",
        (stuck_cutoff,),
    ).fetchall()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_stuck = [s for s in stuck if state["stuck_last_alerted"].get(str(s[0])) != today]

    if not new_failures and not new_stuck:
        print("No new n8n failures or stuck executions (or all within cooldown).")
        if unseen_failures and not dry_run:
            state["alerted_execution_ids"] = list(
                set(state["alerted_execution_ids"]) | {f[0] for f in unseen_failures}
            )[-500:]
            save_state(state)
        return

    lines = ["n8n failure check found something new:", ""]
    if new_failures:
        lines.append(f"FAILED executions ({len(new_failures)}):")
        for eid, wf_id, status, started in new_failures:
            lines.append(f"  - [{status}] workflow '{names.get(wf_id, wf_id)}' execution {eid} at {started}")
        lines.append("")
    if new_stuck:
        lines.append(f"STUCK executions (running > {STUCK_MINUTES}min):")
        for eid, wf_id, started in new_stuck:
            lines.append(f"  - workflow '{names.get(wf_id, wf_id)}' execution {eid} started {started}, still running")
        lines.append("")
    lines.append("Check with: docker exec n8n-n8n-1 ... or see docs/architecture/known-issues.md")
    body = "\n".join(lines)
    print(body)

    if not dry_run:
        password = get_secret("Homelab_SMTP")
        msg = MIMEText(body)
        msg["Subject"] = f"n8n: {len(new_failures)} failure(s), {len(new_stuck)} stuck execution(s)"
        msg["From"] = ALERT_FROM
        msg["To"] = ALERT_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(ALERT_FROM, password)
            server.send_message(msg)
        print("Alert email sent.")

    state["alerted_execution_ids"] = list(
        set(state["alerted_execution_ids"]) | {f[0] for f in unseen_failures}
    )[-500:]
    if new_failures:
        now_iso = now.isoformat()
        for _, wf_id, *_ in new_failures:
            state["workflow_last_alerted"][wf_id] = now_iso
    for eid, *_ in new_stuck:
        state["stuck_last_alerted"][str(eid)] = today
    if not dry_run:
        save_state(state)


if __name__ == "__main__":
    main()
