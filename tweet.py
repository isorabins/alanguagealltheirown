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
DIFF = {"adopted": "+", "rejected": "-", "reverted": "~"}
PREMISE_EVERY = 5   # tweet 0, 5, 10… carry the full premise; the rest stay machine-dry


def compose(rb, rule, n_sent):
    # scores attach rulebook-wide, so they only honestly describe the rulebook a
    # rule was adopted INTO — never why something was rejected; fidelity -1 means
    # the grader output was unparseable, not a real measurement
    s = rule.get("scores") if rule["status"] == "adopted" else None
    if s and s.get("fidelity_pct", -1) < 0:
        s = None
    if n_sent % PREMISE_EVERY == 0:
        if s:
            d = s["token_delta_pct"]
            size = ("the same length as plain English" if d == 0 else
                    f'{abs(d)}% {"shorter" if d < 0 else "longer"} than plain English')
            evidence = f'\n\nStranger-test: {s["fidelity_pct"]}% of meaning survived, {size}.'
        else:
            evidence = ""
        head = f'{REFRAIN}\n\n{LABEL[rule["status"]]}: '
        tail = f'\n\n{adopted_count(rb)} rules in force. {PAGE}'
    else:
        turn = next((e["turn"] for e in reversed(rule["history"]) if isinstance(e, dict)), "?")
        evidence = (f'\nstranger-test: {s["fidelity_pct"]}% meaning · {s["token_delta_pct"]:+d}% size'
                    if s else "")
        head = f'{DIFF[rule["status"]]} {rule["id"]} {rule["status"]} · turn {turn}\n'
        tail = f'\n{adopted_count(rb)} rules live → {PAGE}'
    text = " ".join(rule["text_en"].replace("**", "").split())
    room = MAX_LEN - len(head) - len(evidence) - len(tail) - 2
    if len(text) > room:
        text = text[:room - 1].rstrip() + "…"
    return f'{head}"{text}"{evidence}{tail}'


def post(text, premise=False):
    key, user = env("UPLOAD_POST_API_KEY"), env("UPLOAD_POST_USER")
    if env("TWEET_ENABLE") != "1" or not key or not user:
        log(f"DRY (not posted): {text}")
        return
    platforms = ["x"]
    if premise and env("LINKEDIN_ENABLE") == "1":  # premise-mode posts double as LinkedIn cadence
        platforms.append("linkedin")
    try:
        r = requests.post("https://api.upload-post.com/api/upload_text",
                          headers={"Authorization": f"Apikey {key}"},
                          data={"user": user, "platform[]": platforms, "title": text},
                          timeout=20)
        log(f"posted {platforms} ({r.status_code}): {text}")
    except Exception as e:
        log(f"post FAILED ({e}): {text}")


NOTES_PER_DAY = 2   # field-note drip: history posts oldest-first, capped so it's a stream, not a flood


def post_notes(snap):
    """Field notes (notes.json) to X, oldest unposted first, NOTES_PER_DAY per UTC day.
    Watermark index in tweet-state — notes.json is append-only so an index is stable."""
    notes_f = ROOT / "notes.json"
    if not notes_f.exists():
        return
    notes = json.loads(notes_f.read_text())
    done = snap.get("notes_posted", 0)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if snap.get("notes_day") != today:
        snap["notes_day"], snap["notes_day_count"] = today, 0
    budget = NOTES_PER_DAY - snap.get("notes_day_count", 0)
    for n in notes[done:done + max(0, budget)]:
        text = n.get("tweet") or (" ".join(n.get("note", "").split())[:230].rstrip() + "… " + PAGE)
        if len(text) > MAX_LEN:
            text = text[:MAX_LEN - 1].rstrip() + "…"
        post(text)
        snap["notes_posted"] = snap.get("notes_posted", 0) + 1
        snap["notes_day_count"] = snap.get("notes_day_count", 0) + 1


def main():
    rb = json.loads((STATE / "rulebook.json").read_text())
    cur = {r["id"]: r["status"] for r in rb["rules"]}
    snap_f = STATE / "tweet-state.json"
    snap = json.loads(snap_f.read_text()) if snap_f.exists() else None
    prev, n_sent = (snap["statuses"], snap.get("tweets_sent", 0)) if snap else (None, 0)
    events = [r for r in rb["rules"]
              if prev is not None and r["status"] in TWEET_VERBS and prev.get(r["id"]) != r["status"]]
    if prev is None:
        log(f"bootstrap: snapshot of {len(cur)} rule statuses, nothing tweeted")
    elif len(events) > 3:  # mass change (repair/migration) — one summary, never a flood
        post(f'{REFRAIN}\n\nBig turn: {len(events)} rules changed status at once. '
             f'{adopted_count(rb)} now in force. {PAGE}')
        n_sent += 1
    else:
        for r in events:
            post(compose(rb, r, n_sent), premise=(n_sent % PREMISE_EVERY == 0))
            n_sent += 1
    out = dict(snap) if snap else {}
    out.update({"statuses": cur, "tweets_sent": n_sent})
    post_notes(out)
    snap_f.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a broken tweeter must never take the turn down with it
        log(f"tweet.py error: {e}")
