#!/usr/bin/env python3
"""Best-effort Redis courier. It never writes canonical experiment history."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from collaboration import RedisRest, append_inbox_spool
from state_store import load_json

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "state" / "collaboration-inbox.json"
OUTBOX = ROOT / "state" / "collaboration-outbox.json"


def pull(redis: RedisRest, inbox_path: Path = INBOX, owner: str | None = None,
         limit: int = 4) -> int:
    owner = owner or f"courier-{int(time.time())}"
    try:
        recovered = redis.load_private()
        if recovered:
            append_inbox_spool(inbox_path, [], recovered)
        for queue in ("suggestion", "moderation"):
            for index in range(limit):
                lease_owner = f"{owner}-{queue}-{index}"
                record = redis.claim(queue, lease_owner)
                if not record:
                    break
                append_inbox_spool(inbox_path, [record])
                redis.ack(queue, lease_owner, record.get("id") or "malformed")
        return 0
    except Exception as exc:
        print(f"collaboration courier pull unavailable: {exc.__class__.__name__}", flush=True)
        return 0


def push(redis: RedisRest, outbox_path: Path = OUTBOX) -> int:
    try:
        outbox = load_json(outbox_path, {})
        state = outbox.get("private_state")
        if isinstance(state, dict):
            redis.publish_private(state)
        return 0
    except Exception as exc:
        print(f"collaboration courier push unavailable: {exc.__class__.__name__}", flush=True)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("direction", choices=("pull", "push"))
    args = parser.parse_args()
    try:
        redis = RedisRest(timeout=2.0)
    except Exception as exc:
        print(f"collaboration courier not configured: {exc.__class__.__name__}", flush=True)
        return 0
    return pull(redis) if args.direction == "pull" else push(redis)


if __name__ == "__main__":
    raise SystemExit(main())
