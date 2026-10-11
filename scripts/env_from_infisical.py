#!/usr/bin/env python3
"""Writes secrets from Infisical into a service's .env, without printing them.

    python3 scripts/env_from_infisical.py komga \\
        SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENTID=GOOGLE_OAUTH_CLIENT_ID \\
        SPRING_SECURITY_OAUTH2_CLIENT_REGISTRATION_GOOGLE_CLIENTSECRET=GOOGLE_OAUTH_CLIENT_SECRET

Each argument is ENV_VAR=INFISICAL_SECRET_NAME. Those keys are added to, or
replaced in, <service>/.env; every other line in that file is kept as it is.
All secrets are fetched before anything is written, so a missing one leaves
the file untouched. The file is written with mode 0600. Values never reach
stdout or argv, which keeps them out of terminal scrollback and `ps`.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infisical_client import get_secret  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 3 or any("=" not in a for a in sys.argv[2:]):
        sys.exit(__doc__)
    env_file = REPO_ROOT / sys.argv[1] / ".env"
    if not env_file.parent.is_dir():
        sys.exit(f"No such service directory: {env_file.parent}")
    wanted = dict(a.split("=", 1) for a in sys.argv[2:])

    values, missing = {}, []
    for var, name in wanted.items():
        try:
            values[var] = get_secret(name)
        except Exception:
            missing.append(name)
    if missing:
        sys.exit(f"Not in Infisical (nothing written): {', '.join(missing)}")

    lines = env_file.read_text().splitlines() if env_file.exists() else []
    kept = [l for l in lines if l.split("=", 1)[0].strip() not in values]
    kept += [f"{var}={val}" for var, val in values.items()]
    env_file.write_text("\n".join(kept) + "\n")
    env_file.chmod(0o600)
    print(f"{env_file.relative_to(REPO_ROOT)}: set {', '.join(values)} (values not shown)")


if __name__ == "__main__":
    main()
