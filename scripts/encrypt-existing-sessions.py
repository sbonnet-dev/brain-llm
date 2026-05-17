#!/usr/bin/env python
"""One-shot migration: encrypt plaintext content in existing ``brain.agno_sessions`` rows.

Walks every row in the sessions table and applies AES-256-GCM encryption to:
  * each ``messages[*].content`` string inside ``runs`` JSONB
  * the ``session_data.session_name`` string (custom title)

The encryption helper is idempotent (skips strings already carrying the
``enc:v1:`` prefix), so the script is safe to re-run.

Requires:
  * ``CONVERSATION_ENCRYPTION_KEY`` set in the environment (or in .env)
  * ``DATABASE_URL`` pointing at the Postgres used by brain

Usage:
    python scripts/encrypt-existing-sessions.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make ``app`` importable when invoked as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.crypto import encrypt_text, ensure_key_loaded, is_encrypted  # noqa: E402

SCHEMA = "brain"
TABLE = "agno_sessions"


def _encrypt_runs(runs):
    """Encrypt every ``content`` in ``runs[*].messages[*]`` in place.

    Returns True if any change was made.
    """
    if not isinstance(runs, list):
        return False
    changed = False
    for run in runs:
        if not isinstance(run, dict):
            continue
        messages = run.get("messages")
        if not isinstance(messages, list):
            continue
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if isinstance(content, str) and content and not is_encrypted(content):
                msg["content"] = encrypt_text(content)
                changed = True
    return changed


def _encrypt_session_data(session_data):
    """Encrypt ``session_name`` (if any) in place. Returns True if changed."""
    if not isinstance(session_data, dict):
        return False
    name = session_data.get("session_name")
    if isinstance(name, str) and name and not is_encrypted(name):
        session_data["session_name"] = encrypt_text(name)
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    args = parser.parse_args()

    ensure_key_loaded()
    db_url = get_settings().database_url
    if db_url.startswith("sqlite"):
        print(
            "[warn] DATABASE_URL points at SQLite — sessions table is owned by Agno, "
            "make sure this is the right database.",
            file=sys.stderr,
        )

    print(f"[info] Connecting to {db_url}")
    engine = create_engine(db_url, future=True)

    qualified = f"{SCHEMA}.{TABLE}" if not db_url.startswith("sqlite") else TABLE

    with engine.begin() as conn:
        rows = conn.execute(
            text(f"SELECT session_id, runs, session_data FROM {qualified}")
        ).fetchall()

        print(f"[info] {len(rows)} session(s) found")
        touched = 0
        for row in rows:
            session_id = row[0]
            runs = row[1]
            session_data = row[2]

            # The driver may give us already-parsed JSON, or a string.
            if isinstance(runs, str):
                try:
                    runs = json.loads(runs)
                except Exception:
                    runs = None
            if isinstance(session_data, str):
                try:
                    session_data = json.loads(session_data)
                except Exception:
                    session_data = None

            runs_changed = _encrypt_runs(runs)
            data_changed = _encrypt_session_data(session_data)

            if not (runs_changed or data_changed):
                continue

            touched += 1
            if args.dry_run:
                print(f"  [dry-run] would update session {session_id}")
                continue

            conn.execute(
                text(
                    f"UPDATE {qualified} SET runs = :runs, session_data = :sd "
                    "WHERE session_id = :sid"
                ),
                {
                    "runs": json.dumps(runs) if runs is not None else None,
                    "sd": json.dumps(session_data) if session_data is not None else None,
                    "sid": session_id,
                },
            )
            print(f"  [ok] encrypted session {session_id}")

        print(f"[done] {touched} session(s) {'would be' if args.dry_run else ''} updated")

    return 0


if __name__ == "__main__":
    sys.exit(main())
