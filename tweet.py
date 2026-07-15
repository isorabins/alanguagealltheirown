#!/usr/bin/env python3
"""Dry changelog to X via upload-post — fired by run_turn.sh after every turn.

Tweets only rule status changes (adopted / rejected / reverted), never raw
proposals. Without TWEET_ENABLE=1 plus credentials in .env it only logs what
it would have posted. A tweet that fails is logged and dropped — the loop
never waits on, retries for, or dies over Twitter.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
PAGE = "alanguagealltheirown.com"
MAX_LEN = 275          # under X's 280 so upload-post never auto-threads
TWEET_VERBS = ("adopted", "rejected", "reverted")


def env(name):
    if (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


def log(msg):
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


def adopted_count(rb):
    return sum(1 for r in rb["rules"] if r["status"] == "adopted")


REFRAIN = "Two AIs are inventing a language, one tested rule at a time."
LABEL = {"adopted": "New rule adopted", "rejected": "Rule rejected",
         "reverted": "Rule un-adopted"}


def compose(rb, rule):
    # scores attach rulebook-wide, so they only honestly describe the rulebook a
    # rule was adopted INTO — never why something was rejected
    s = rule.get("scores") if rule["status"] == "adopted" else None
    if s:
        d = s["token_delta_pct"]
        size = ("the same length as plain English" if d == 0 else
                f'{abs(d)}% {"shorter" if d < 0 else "longer"} than plain English')
        evidence = f'\n\nStranger-test: {s["fidelity_pct"]}% of meaning survived, {size}.'
    else:
        evidence = ""
    head = f'{REFRAIN}\n\n{LABEL[rule["status"]]}: '
    tail = f'\n\n{adopted_count(rb)} rules in force. {PAGE}'
    text = " ".join(rule["text_en"].replace("**", "").split())
    room = MAX_LEN - len(head) - len(evidence) - len(tail) - 2
    if len(text) > room:
        text = text[:room - 1].rstrip() + "…"
    return f'{head}"{text}"{evidence}{tail}'


def post(text):
    key, user = env("UPLOAD_POST_API_KEY"), env("UPLOAD_POST_USER")
    if env("TWEET_ENABLE") != "1" or not key or not user:
        log(f"DRY (not posted): {text}")
        return
    try:
        r = requests.post("https://api.upload-post.com/api/upload_text",
                          headers={"Authorization": f"Apikey {key}"},
                          data={"user": user, "platform[]": "x", "title": text},
                          timeout=20)
        log(f"posted ({r.status_code}): {text}")
    except Exception as e:
        log(f"post FAILED ({e}): {text}")


def main():
    rb = json.loads((STATE / "rulebook.json").read_text())
    cur = {r["id"]: r["status"] for r in rb["rules"]}
    snap_f = STATE / "tweet-state.json"
    prev = json.loads(snap_f.read_text())["statuses"] if snap_f.exists() else None
    snap_f.write_text(json.dumps({"statuses": cur}, indent=1) + "\n")
    if prev is None:
        log(f"bootstrap: snapshot of {len(cur)} rule statuses, nothing tweeted")
        return
    events = [r for r in rb["rules"]
              if r["status"] in TWEET_VERBS and prev.get(r["id"]) != r["status"]]
    if not events:
        return
    if len(events) > 3:  # mass change (repair/migration) — one summary, never a flood
        post(f'{REFRAIN}\n\nBig turn: {len(events)} rules changed status at once. '
             f'{adopted_count(rb)} now in force. {PAGE}')
        return
    for r in events:
        post(compose(rb, r))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a broken tweeter must never take the turn down with it
        log(f"tweet.py error: {e}")
