#!/usr/bin/env python3
"""A Language All Their Own — the entire engine.

Two agents negotiate an AI-to-AI language; every rule survives (or dies by)
an encode/decode test against a fresh decoder. This file is deliberately all
the code there is: plumbing only, the LLMs do the language.
"""
import argparse
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_A = "deepseek/deepseek-v3.2"
MODEL_B = "deepseek/deepseek-v3.2"
MODEL_DECODER = "deepseek/deepseek-v3.2"
MODEL_GRADER = "deepseek/deepseek-v3.2"
PRICE_IN = 0.2145 / 1e6   # $/token, OpenRouter listing 2026-07-14
PRICE_OUT = 0.32175 / 1e6

TEST_EVERY = 3      # every Nth turn is a test turn
WINDOW = 12         # conversation events each agent sees
SPEND_CAP = 4.50    # dollars, hard stop across all runs
AGENT_TEMP = 0.9

_key = None
_no_reasoning_field = False
_probe_overhead = None
_probe_cache = {}


def api_key():
    global _key
    if _key is None:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                _key = line.split("=", 1)[1].strip()
    if not _key:
        sys.exit("no OPENROUTER_API_KEY in .env")
    return _key


def load(name, default):
    f = STATE / name
    return json.loads(f.read_text()) if f.exists() else default


def save(name, obj):
    (STATE / name).write_text(json.dumps(obj, indent=1))


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def call(model, system, user, max_tokens=600, temperature=0.7, meta=None):
    """One chat call. Returns (text, usage). Retries transient failures."""
    global _no_reasoning_field
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": user}
    ]
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature,
            "provider": {"order": ["deepseek"]}}  # prefer one provider: token accounting must be consistent
    if not _no_reasoning_field:
        body["reasoning"] = {"enabled": False}
    headers = {"Authorization": f"Bearer {api_key()}",
               "HTTP-Referer": "https://alanguagealltheirown.com",
               "X-Title": "a-language-all-their-own"}
    delays = [0, 3, 8, 20, 45]
    for i, d in enumerate(delays):
        if d:
            time.sleep(d)
        try:
            r = requests.post(API_URL, headers=headers, json=body, timeout=180)
        except requests.RequestException as e:
            print(f"  ! network {e.__class__.__name__}, retry {i}", flush=True)
            continue
        if r.status_code == 400 and not _no_reasoning_field:
            _no_reasoning_field = True
            body.pop("reasoning", None)
            continue
        if r.status_code in (429, 500, 502, 503, 520, 524):
            print(f"  ! http {r.status_code}, retry {i}", flush=True)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"api {r.status_code}: {r.text[:300]}")
        d = r.json()
        if "error" in d:
            print(f"  ! provider error {str(d['error'])[:120]}, retry {i}", flush=True)
            continue
        usage = d.get("usage", {})
        if meta is not None:
            meta["spend_usd"] = round(
                meta.get("spend_usd", 0.0)
                + usage.get("prompt_tokens", 0) * PRICE_IN
                + usage.get("completion_tokens", 0) * PRICE_OUT, 6)
        return d["choices"][0]["message"]["content"] or "", usage
    raise RuntimeError("api: retries exhausted")


def token_count(text, meta):
    """Exact token size of standalone text: probe call, prompt_tokens minus overhead.
    Probe-based so reasoning/completion accounting can never contaminate it."""
    global _probe_overhead
    if text in _probe_cache:
        return _probe_cache[text]
    if _probe_overhead is None:
        _, u = call(MODEL_GRADER, None, "x", max_tokens=1, temperature=0, meta=meta)
        _probe_overhead = u["prompt_tokens"] - 1
    _, u = call(MODEL_GRADER, None, text, max_tokens=1, temperature=0, meta=meta)
    n = max(1, u["prompt_tokens"] - _probe_overhead)
    if n <= 2 and len(text) > 12:  # implausible: provider drift broke calibration — recalibrate once
        _probe_overhead = None
        _probe_cache.clear()
        _, u0 = call(MODEL_GRADER, None, "x", max_tokens=1, temperature=0, meta=meta)
        _probe_overhead = u0["prompt_tokens"] - 1
        _, u = call(MODEL_GRADER, None, text, max_tokens=1, temperature=0, meta=meta)
        n = max(1, u["prompt_tokens"] - _probe_overhead)
    _probe_cache[text] = n
    return n


def render_rulebook(rb):
    if not rb["rules"]:
        return "The rulebook is empty. No rules exist yet."
    lines = [f"RULEBOOK v{rb['version']} — {rb['kernel_tokens']} tokens of context, every message pays for it"]
    for r in rb["rules"]:
        s = r["scores"]
        score = f" (last test: fidelity {s['fidelity_pct']}, tokens {s['token_delta_pct']:+d}%)" if s else ""
        lines.append(f"{r['id']} [{r['status']}] {r['text_en']}{score}")
    return "\n".join(lines)


def render_window(conv):
    out = []
    for e in conv[-WINDOW:]:
        if e["type"] == "measure":
            out.append(f"[turn {e['turn']} — MEASUREMENT] \"{e['text']}\" = {e['tokens']} tokens (exact)")
            continue
        if e["type"] == "test":
            out.append(
                f"[turn {e['turn']} — LIVE TEST | payload: {e['payload']}]\n"
                f"original {e['orig_tokens']} tokens -> encoded {e['enc_tokens']} tokens "
                f"({e['token_delta_pct']:+d}%) | decode fidelity {e['fidelity']}/100\n"
                f"encoded: {e['encoded']}\n"
                f"fresh decoder returned: {e['decoded'][:400]}\n"
                f"grader: {e['lost']}")
        else:
            out.append(f"[turn {e['turn']}] AGENT {e['agent']}:\n{e['content']}")
    return "\n\n".join(out) if out else "(no conversation yet — the rulebook is empty and you speak first)"


def rationale_for(text, line):
    """The paragraph around a PROPOSE/ADOPT/REJECT line, minus verb lines — the 'why'."""
    paras = text.split("\n\n")
    idx = next((i for i, p in enumerate(paras) if line in p), 0)
    for cand in (paras[idx], paras[idx - 1] if idx else ""):
        why = " ".join(l for l in cand.splitlines()
                       if not re.match(r"\s*\**(PROPOSE|ADOPT|REJECT|REVISE)", l)).strip()
        if len(why) > 20:
            return why[:280]
    return ""


def apply_conventions(text, rb, turn, agent="?"):
    changed = False
    for line in text.splitlines():
        m = re.match(r"\s*\**(PROPOSE|ADOPT|REJECT|REVISE)\**\s*:\s*(.+)", line)
        if not m:
            continue
        verb, rest = m.group(1), m.group(2).strip().strip("*").strip()
        rest = re.sub(r"[‐‑‒–—]", "-", rest)  # agents emit unicode hyphens in rule ids
        inner = re.match(r"(PROPOSE|ADOPT|REJECT|REVISE)\**\s*:\s*(.+)", rest)
        if verb == "PROPOSE" and inner:
            # "PROPOSE: REJECT: rule-014" is a motion, not a rule — act on the inner
            # verb instead of minting a rule whose text is a verb line (t63/t73/t74)
            verb, rest = inner.group(1), inner.group(2).strip().strip("*").strip()
        if verb == "PROPOSE":
            if any(r["text_en"].strip() == rest for r in rb["rules"]):
                continue  # identical re-proposal (echo agreement) — don't duplicate
            rid = f"rule-{rb['next_id']:03d}"
            rb["next_id"] += 1
            rb["rules"].append({"id": rid, "text_en": rest, "status": "proposed",
                                "proposed_turn": turn, "scores": None,
                                "history": [{"verb": "proposed", "turn": turn, "agent": agent,
                                             "why": rationale_for(text, line)}]})
            changed = True
            continue
        idm = re.search(r"rule-(\d+)", rest)
        rule = next((r for r in rb["rules"] if idm and r["id"] == f"rule-{int(idm.group(1)):03d}"), None)
        if not rule:
            continue
        if verb == "ADOPT" and rule["status"] in ("proposed", "reverted"):
            rule["status"] = "adopted"
        elif verb == "REJECT":
            rule["status"] = "reverted" if rule["status"] == "adopted" else "rejected"
        elif verb == "REVISE":
            new = rest.split("->", 1)
            if len(new) == 2:
                rule["text_en"] = new[1].strip().strip("*").strip()
                rule["status"] = "proposed"
            else:
                continue
        rule["history"].append({"verb": verb.lower(), "turn": turn, "agent": agent,
                                "why": rationale_for(text, line)})
        changed = True
    return changed


def write_viewer_state(conv, rb, meta):
    (ROOT / "viewer" / "state.js").write_text(
        "window.STATE = " + json.dumps(
            {"conversation": conv, "rulebook": rb,
             "meta": {"spend_usd": meta.get("spend_usd", 0), "model": MODEL_A,
                      "updated": now_iso(), "run": meta.get("run", "local")}}) + ";\n")


def agent_turn(conv, rb, meta, turn):
    agent = "B" if meta.get("last_agent") == "A" else "A"
    meta["last_agent"] = agent
    model = MODEL_A if agent == "A" else MODEL_B
    prompt = (ROOT / "prompts" / f"agent_{agent.lower()}.md").read_text()
    system = (f"{prompt}\n\n=== CURRENT RULEBOOK ===\n{render_rulebook(rb)}\n"
              f"=== STATE ===\nturn {turn} | next live test at turn "
              f"{((turn // TEST_EVERY) + 1) * TEST_EVERY}")
    user = render_window(conv) + f"\n\nIt is turn {turn}. You are Agent {agent}. Respond."
    text, usage = call(model, system, user, max_tokens=650, temperature=AGENT_TEMP, meta=meta)
    conv.append({"turn": turn, "agent": agent, "type": "message", "content": text.strip(),
                 "tokens": usage.get("completion_tokens", 0)})
    for mm in list(re.finditer(r"^\s*\**MEASURE\**\s*:\s*(.+)$", text, re.M))[:2]:
        probe_text = mm.group(1).strip().strip("`")
        n = token_count(probe_text, meta)
        conv.append({"turn": turn, "agent": "harness", "type": "measure",
                     "text": probe_text[:120], "tokens": n})
        print(f"[t{turn} MEASURE] \"{probe_text[:40]}\" = {n}tok", flush=True)
    if apply_conventions(text, rb, turn, agent):
        rb["version"] = f"0.{rb['changes'] + 1}"
        rb["changes"] += 1
        rb["kernel_tokens"] = token_count(render_rulebook(rb), meta)
    print(f"[t{turn} {agent}] {usage.get('completion_tokens', 0)}tok  "
          f"rules:{len(rb['rules'])}  ${meta['spend_usd']:.3f}", flush=True)


DOMAINS = ["logistics", "software operations", "event planning", "food service", "travel",
           "equipment maintenance", "publishing", "customer support", "farming",
           "construction", "lab work", "retail"]


def gen_payload(meta):
    """A fresh, never-seen test message — written blind: the generator sees neither the
    rulebook nor the conversation, so the exam can't be taught to (payloads were a fixed
    set of 13 files until test #24; those files are now the transfer-test battery)."""
    n = meta.get("tests_run", 0)
    kind = ("prose", "task", "data")[n % 3]
    domain = DOMAINS[(n // 3) % len(DOMAINS)]
    prompt = ((ROOT / "prompts" / "payloadgen.md").read_text()
              .replace("{CATEGORY}", kind).replace("{DOMAIN}", domain))
    for _ in range(2):
        text, _ = call(MODEL_A, prompt, "Write the message now.",
                       max_tokens=400, temperature=1.0, meta=meta)
        text = text.strip().strip('"').strip()
        if 200 <= len(text) <= 900:
            return f"gen-{kind}-{domain.split()[0]}", text
    return None, None


def test_turn(conv, rb, meta, turn):
    pname, payload = gen_payload(meta)
    if payload is None:  # generator failed twice — fall back to the fixed battery
        by_kind = {}
        for f in sorted((ROOT / "payloads").glob("*.txt")):
            by_kind.setdefault(f.name.split("-")[0], []).append(f)
        kinds = sorted(by_kind)  # interleave prose/task/data so no type dominates
        payloads = [ks[i] for i in range(max(len(v) for v in by_kind.values()))
                    for ks in (by_kind[k] for k in kinds) if i < len(ks)]
        p = payloads[meta.get("tests_run", 0) % len(payloads)]
        pname, payload = p.name, p.read_text().strip()
    rbook = render_rulebook(rb)
    enc_sys = ("You are the encoder. Encode the message below into the project language "
               "using ONLY this rulebook. Where the rulebook is silent, fall back to plain "
               "English for that part. Output ONLY the encoded message, nothing else.\n\n" + rbook)
    encoded, _ = call(MODEL_A, enc_sys, payload, max_tokens=1000, temperature=0.3, meta=meta)
    dec_sys = ("You are a fresh agent. You have never seen any prior conversation. Below is the "
               "complete rulebook of a constructed language. Decode the message you receive: "
               "reconstruct the original content as faithfully as you can. Do not invent anything "
               "the message does not encode. Output ONLY the reconstruction.\n\n" + rbook)
    decoded, _ = call(MODEL_DECODER, dec_sys, encoded.strip(), max_tokens=1000, temperature=0.1, meta=meta)
    grade_sys = (ROOT / "prompts" / "grader.md").read_text()
    graded, _ = call(MODEL_GRADER, grade_sys,
                     f"ORIGINAL:\n{payload}\n\nDECODED:\n{decoded.strip()}",
                     max_tokens=200, temperature=0, meta=meta)
    gm = re.search(r"\{.*\}", graded, re.S)
    try:
        g = json.loads(gm.group(0)) if gm else {}
    except json.JSONDecodeError:
        g = {}
    fidelity = max(0, min(100, int(g.get("fidelity", -1)))) if g.get("fidelity") is not None else -1
    lost = str(g.get("lost", "grader output unparseable"))[:300]
    orig_t = token_count(payload, meta)
    enc_t = token_count(encoded.strip(), meta)
    delta = round((enc_t - orig_t) / orig_t * 100)
    meta["tests_run"] = meta.get("tests_run", 0) + 1
    conv.append({"turn": turn, "agent": "harness", "type": "test", "payload": pname,
                 "original": payload, "orig_tokens": orig_t, "enc_tokens": enc_t,
                 "token_delta_pct": delta, "fidelity": fidelity, "lost": lost,
                 "encoded": encoded.strip(), "decoded": decoded.strip(), "tokens": enc_t})
    for r in rb["rules"]:
        if r["status"] in ("proposed", "adopted"):
            r["scores"] = {"token_delta_pct": delta, "fidelity_pct": fidelity}
            r["history"].append(f"tested turn {turn}: fid {fidelity}, {delta:+d}%")
    print(f"[t{turn} TEST] {pname}  {orig_t}->{enc_t}tok ({delta:+d}%)  fid {fidelity}  "
          f"${meta['spend_usd']:.3f}", flush=True)


def run(turns):
    STATE.mkdir(exist_ok=True)
    conv = load("conversation.json", [])
    rb = load("rulebook.json", {"version": "0.0", "kernel_tokens": 0, "changes": 0,
                                "next_id": 1, "rules": []})
    meta = load("meta.json", {"spend_usd": 0.0, "last_agent": None, "tests_run": 0,
                              "started": now_iso()})
    start_turn = (conv[-1]["turn"] + 1) if conv else 1
    for turn in range(start_turn, start_turn + turns):
        if meta["spend_usd"] >= SPEND_CAP:
            print(f"SPEND CAP hit (${meta['spend_usd']:.2f}) — stopping.", flush=True)
            break
        if turn % TEST_EVERY == 0:
            test_turn(conv, rb, meta, turn)
        else:
            agent_turn(conv, rb, meta, turn)
        save("conversation.json", conv)
        save("rulebook.json", rb)
        save("meta.json", meta)
        write_viewer_state(conv, rb, meta)
    print(f"done. turns {start_turn}..{turn}  rules {len(rb['rules'])}  "
          f"spend ${meta['spend_usd']:.3f}", flush=True)


def archive(name):
    dest = STATE / "tuning-runs" / name
    dest.mkdir(parents=True, exist_ok=True)
    for f in ("conversation.json", "rulebook.json", "meta.json"):
        if (STATE / f).exists():
            shutil.move(str(STATE / f), str(dest / f))
    for pf in (ROOT / "prompts").glob("*.md"):
        shutil.copy(str(pf), str(dest / pf.name))
    print(f"archived state + prompt snapshot -> state/tuning-runs/{name}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=6)
    ap.add_argument("--archive", help="archive current state under this name and reset")
    args = ap.parse_args()
    if args.archive:
        archive(args.archive)
    else:
        run(args.turns)
