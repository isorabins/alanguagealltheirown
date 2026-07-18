#!/usr/bin/env python3
"""The control — a dumb minifier baseline for every exam, run by a script, not an AI.

For each exam in state/conversation.json, compress the ORIGINAL message mechanically
(lowercase, strip punctuation and articles, leave anything containing a digit untouched)
and count the result with the same provider-pinned tokenizer probe the loop uses.
If the agents' language saved no more than this script, the language does nothing.
Writes state/probe.json (incremental — already-counted exams are never re-billed).
Fired by run_turn.sh after every turn; failure never blocks the loop.
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v3.2"   # loop.py's grader model: token accounting must share one tokenizer
PRICE_IN = 0.2145 / 1e6
MAX_NEW_PER_RUN = 100

DROP = {"the", "a", "an", "please"}
EDGE = ".,;:!?\"'()[]{}“”‘’"


def minify(text):
    out = []
    for w in text.split():
        if any(c.isdigit() for c in w):
            out.append(w)                      # numbers, IDs, dates, units: verbatim
            continue
        w = w.strip(EDGE).lower()
        if w and w not in DROP:
            out.append(w)
    return " ".join(out)


def api_key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("no OPENROUTER_API_KEY in .env")


def probe(text, key, spend):
    """prompt_tokens of a max_tokens=1 call, minus overhead — loop.py's exact method."""
    body = {"model": MODEL, "messages": [{"role": "user", "content": text}],
            "max_tokens": 1, "temperature": 0, "provider": {"order": ["deepseek"]},
            "reasoning": {"enabled": False}}
    headers = {"Authorization": f"Bearer {key}",
               "HTTP-Referer": "https://alanguagealltheirown.com",
               "X-Title": "a-language-all-their-own"}
    for d in (0, 3, 10, 30):
        if d:
            time.sleep(d)
        try:
            r = requests.post(API_URL, headers=headers, json=body, timeout=60)
        except requests.RequestException:
            continue
        if r.status_code != 200:
            continue
        j = r.json()
        if "error" in j or "usage" not in j:
            continue
        n = j["usage"].get("prompt_tokens", 0)
        spend[0] += n * PRICE_IN
        return n
    raise RuntimeError("probe: retries exhausted")


def main():
    conv = json.loads((STATE / "conversation.json").read_text())
    pf = STATE / "probe.json"
    data = json.loads(pf.read_text()) if pf.exists() else {"exams": [], "spend_usd": 0.0}
    done = {e["turn"] for e in data["exams"]}
    todo = [e for e in conv if e.get("type") == "test" and e.get("original")
            and e["turn"] not in done][:MAX_NEW_PER_RUN]
    if not todo:
        return
    key = api_key()
    spend = [0.0]
    overhead = probe("x", key, spend) - 1
    for e in todo:
        n = max(1, probe(minify(e["original"]), key, spend) - overhead)
        data["exams"].append({"turn": e["turn"], "orig_tokens": e["orig_tokens"],
                              "enc_tokens": e["enc_tokens"], "min_tokens": n,
                              "fidelity": e.get("fidelity", -1)})
        print(f"t{e['turn']}: orig {e['orig_tokens']} enc {e['enc_tokens']} minified {n}", flush=True)
    data["exams"].sort(key=lambda x: x["turn"])
    data["spend_usd"] = round(data.get("spend_usd", 0.0) + spend[0], 6)
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["method"] = ("lowercase; strip surrounding punctuation; drop the/a/an/please; "
                      "words containing digits kept verbatim; token-counted by the same "
                      "provider-pinned probe as the loop")
    pf.write_text(json.dumps(data, indent=1) + "\n")
    print(f"probe: +{len(todo)} exams, run cost ${spend[0]:.4f}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # the control must never take a turn down with it
        print(f"probe.py error: {e}", flush=True)
