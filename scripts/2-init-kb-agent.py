#!/usr/bin/env python3
"""Upload sample files into the KB declared in agents-config.yaml and ingest.

Prerequisite: run scripts/1-init-agents.py first to create the providers,
models, KB and agent. This script only feeds files into the KB and triggers
Qdrant ingestion.

Usage:
    python scripts/2-init-kb-agent.py [--config PATH] [--base-url URL]
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from _shared import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    find_by_name,
    first_kb,
    load_config,
    make_loggers,
    resolve_samples_dir,
)

_log, _ok, _warn, _err = make_loggers("init-kb-agent")


def _get(client: httpx.Client, path: str) -> Any:
    r = client.get(path)
    r.raise_for_status()
    return r.json()


def upload_files(client: httpx.Client, kb_id: int, samples_dir: Path) -> list[dict]:
    if not samples_dir.is_dir():
        _err(f"Sample dir not found: {samples_dir}")

    existing = {f["filename"] for f in _get(client, f"/api/v1/knowledge/bases/{kb_id}/files")}
    uploaded: list[dict] = []

    for path in sorted(samples_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name in existing:
            _log(f"File '{path.name}' already uploaded — skipping")
            continue

        mime = mimetypes.guess_type(path.name)[0] or "text/plain"
        _log(f"Uploading '{path.name}' ({mime})")
        with path.open("rb") as fh:
            r = client.post(
                f"/api/v1/knowledge/bases/{kb_id}/files",
                files={"file": (path.name, fh, mime)},
            )
        if r.status_code >= 400:
            _err(f"Upload failed for {path.name}: {r.status_code} {r.text}")
        uploaded.append(r.json())
        _ok(f"Uploaded '{path.name}' as file id={r.json()['id']}")

    return uploaded


def ingest(client: httpx.Client, kb_id: int) -> dict:
    _log(f"Triggering ingestion for KB id={kb_id} …")
    r = client.post(f"/api/v1/knowledge/ingest/kb/{kb_id}", timeout=600)
    if r.status_code >= 400:
        _err(f"Ingestion failed: {r.status_code} {r.text}")
    data = r.json()
    _ok(
        f"Ingestion done — status={data['status_id']} "
        f"processed={data['files_processed']} failed={data['files_failed']}"
    )
    if data.get("message"):
        _warn(f"Ingestion message: {data['message']}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    try:
        config, config_path = load_config(args.config)
        kb_cfg = first_kb(config)
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))

    samples_dir = resolve_samples_dir(config_path, kb_cfg)

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=60) as client:
        _log(f"Checking API at {args.base_url}/health …")
        try:
            _get(client, "/health")
        except httpx.HTTPError as exc:
            _err(f"API not reachable: {exc}")

        kbs = _get(client, "/api/v1/knowledge/bases")
        kb = find_by_name(kbs, kb_cfg["name"])
        if kb is None:
            _err(
                f"KB '{kb_cfg['name']}' not found. Run "
                "`python scripts/1-init-agents.py` first."
            )

        _log(f"Using KB '{kb['name']}' (id={kb['id']}, embedder={kb.get('embedder')})")
        upload_files(client, kb["id"], samples_dir)
        ingest(client, kb["id"])

    print()
    _ok(f"KB '{kb_cfg['name']}' ready. Run `python scripts/3-test-kb-agent.py` to query it.")


if __name__ == "__main__":
    main()
