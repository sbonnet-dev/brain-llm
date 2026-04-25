#!/usr/bin/env python3
"""Run the test questions from agents-config.yaml against the KB-backed agent.

Usage:
    python scripts/3-test-kb-agent.py [--config PATH] [--base-url URL]
                                      [--question Q ...] [--stream]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from _shared import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    find_by_name,
    kb_agent,
    load_config,
    make_loggers,
)

_log, _ok, _warn, _err = make_loggers("test-kb-agent")


def _get(client: httpx.Client, path: str) -> Any:
    r = client.get(path)
    r.raise_for_status()
    return r.json()


def run_blocking(client: httpx.Client, agent_id: int, question: str) -> str:
    r = client.post(
        f"/api/v1/agents/{agent_id}/run",
        json={"message": question, "stream": False},
        timeout=300,
    )
    if r.status_code >= 400:
        _err(f"Run failed ({r.status_code}): {r.text}")
    data = r.json()
    return data.get("content") or json.dumps(data, indent=2)


def run_streaming(client: httpx.Client, agent_id: int, question: str) -> str:
    chunks: list[str] = []
    with client.stream(
        "POST",
        f"/api/v1/agents/{agent_id}/run",
        json={"message": question, "stream": True},
        timeout=300,
    ) as response:
        if response.status_code >= 400:
            _err(f"Run failed ({response.status_code}): {response.read().decode(errors='replace')}")
        for line in response.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            try:
                frame = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if frame.get("done"):
                break
            chunk = frame.get("content")
            if chunk:
                sys.stdout.write(chunk)
                sys.stdout.flush()
                chunks.append(chunk)
    sys.stdout.write("\n")
    return "".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--question", action="append", help="Override the YAML questions (repeatable).")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()

    try:
        config, _ = load_config(args.config)
        agent_cfg = kb_agent(config)
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))

    questions = args.question or (config.get("test") or {}).get("questions") or []
    if not questions:
        _err("No questions to ask: declare them under 'test.questions' or pass --question.")

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30) as client:
        try:
            _get(client, "/health")
        except httpx.HTTPError as exc:
            _err(f"API not reachable: {exc}")

        agents = _get(client, "/api/v1/agents")
        agent = find_by_name(agents, agent_cfg["name"])
        if agent is None:
            _err(
                f"Agent '{agent_cfg['name']}' not found on the API. Run "
                "`python scripts/1-init-agents.py` first."
            )

        _log(f"Using agent '{agent['name']}' (id={agent['id']}, model_id={agent['model_id']})")

        for q in questions:
            print()
            print("-" * 72)
            _log(f"Q: {q}")
            if args.stream:
                run_streaming(client, agent["id"], q)
            else:
                print(f"A: {run_blocking(client, agent['id'], q)}")

    print()
    _ok("Done.")


if __name__ == "__main__":
    main()
