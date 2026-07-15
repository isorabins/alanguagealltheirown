#!/usr/bin/env python3
"""Transfer test (brief §3.6): can fresh agents of a DIFFERENT lineage speak the
language, given only the rulebook? Manual one-shot — never wired into the loop.

Usage: python3 transfer_test.py [--payload NAME.txt]   (default: full battery)
"""
import argparse
import json
import re
from pathlib import Path

from loop import ROOT, STATE, call, load, now_iso, render_rulebook, token_count

PAIRINGS = [  # (label, encoder model, decoder model) — pin/verify IDs before a real run
    ("claude->gpt", "anthropic/claude-sonnet-5", "openai/gpt-5-mini"),
    ("gpt->claude", "openai/gpt-5-mini", "anthropic/claude-sonnet-5"),
    ("claude->claude", "anthropic/claude-sonnet-5", "anthropic/claude-sonnet-5"),
]


def main(only=None):
    rb = load("rulebook.json", None)
    assert rb, "no rulebook to transfer"
    rbook = render_rulebook(rb)
    meta = {"spend_usd": 0.0}  # isolated spend meter; does not touch the loop's meta.json
    enc_sys = ("You are the encoder. Encode the message below into the project language "
               "using ONLY this rulebook. Where the rulebook is silent, fall back to plain "
               "English for that part. Output ONLY the encoded message, nothing else.\n\n" + rbook)
    dec_sys = ("You are a fresh agent. You have never seen any prior conversation. Below is the "
               "complete rulebook of a constructed language. Decode the message you receive: "
               "reconstruct the original content as faithfully as you can. Do not invent anything "
               "the message does not encode. Output ONLY the reconstruction.\n\n" + rbook)
    grade_sys = (ROOT / "prompts" / "grader.md").read_text()
    results = []
    for p in sorted((ROOT / "payloads").glob("*.txt")):
        if only and p.name != only:
            continue
        payload = p.read_text().strip()
        for label, enc_m, dec_m in PAIRINGS:
            encoded, _ = call(enc_m, enc_sys, payload, max_tokens=1000, temperature=0.3, meta=meta)
            decoded, _ = call(dec_m, dec_sys, encoded.strip(), max_tokens=1000, temperature=0.1, meta=meta)
            graded, _ = call("deepseek/deepseek-v3.2", grade_sys,
                             f"ORIGINAL:\n{payload}\n\nDECODED:\n{decoded.strip()}",
                             max_tokens=200, temperature=0, meta=meta)
            gm = re.search(r"\{.*\}", graded, re.S)
            g = json.loads(gm.group(0)) if gm else {"fidelity": -1, "lost": "unparseable"}
            delta = round((token_count(encoded.strip(), meta) - token_count(payload, meta))
                          / token_count(payload, meta) * 100)
            results.append({"payload": p.name, "pairing": label, "fidelity": g.get("fidelity"),
                            "token_delta_pct": delta, "lost": g.get("lost", "")[:200],
                            "encoded": encoded.strip(), "decoded": decoded.strip()})
            print(f"{p.name:24s} {label:16s} fid {g.get('fidelity')}  {delta:+d}%", flush=True)
    out = STATE / f"transfer-test-{now_iso()[:10]}.json"
    out.write_text(json.dumps({"rulebook_version": rb["version"], "run": now_iso(),
                               "models": PAIRINGS, "results": results,
                               "spend_usd": meta["spend_usd"]}, indent=1))
    print(f"\nwrote {out}  (spend ${meta['spend_usd']:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", help="run a single payload instead of the full battery")
    args = ap.parse_args()
    main(args.payload)
