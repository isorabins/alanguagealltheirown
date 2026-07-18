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

from probe import minify   # the control's dumb minifier — one recipe, everywhere

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_A = "deepseek/deepseek-v3.2"
MODEL_B = "deepseek/deepseek-v3.2"
MODEL_DECODER = "moonshotai/kimi-k2.6"  # a FOREIGN decoder: the stranger must not share the negotiators' weights
MODEL_GRADER = "deepseek/deepseek-v3.2"
PRICE_IN = 0.2145 / 1e6   # $/token, OpenRouter listing 2026-07-14
PRICE_OUT = 0.32175 / 1e6

TEST_EVERY = 3      # every Nth turn is a test turn
WINDOW = 30         # conversation events each agent sees
SPEND_CAP = 25.00   # dollars, hard stop across all runs — anomaly tripwire, ~50 days at gloves-off burn
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
            "temperature": temperature}
    if model.startswith("deepseek/"):
        # pin deepseek calls to one provider: all token accounting (probes, MEASURE)
        # flows through these and must stay on a single tokenizer/provider. Foreign
        # models (the decoder) stay unpinned — their usage never feeds accounting.
        body["provider"] = {"order": ["deepseek"]}
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
        if r["status"] in ("rejected", "reverted"):
            # tombstones stay as memory but render as index cards, not full corpses —
            # the graveyard was most of what every call paid for (full record: git + page)
            died = next((e["turn"] for e in reversed(r["history"])
                         if isinstance(e, dict) and e.get("verb") in ("reject", "rejected")), "?")
            stub = r["text_en"][:60].rstrip() + ("…" if len(r["text_en"]) > 60 else "")
            kill = f" — died at fidelity {s['fidelity_pct']}, {s['token_delta_pct']:+d}%" if s else ""
            lines.append(f"{r['id']} [{r['status']} t{died}] {stub}{kill}")
            continue
        score = f" (last test: fidelity {s['fidelity_pct']}, tokens {s['token_delta_pct']:+d}%)" if s else ""
        lines.append(f"{r['id']} [{r['status']}] {r['text_en']}{score}")
    return "\n".join(lines)


DECODE_VIEW_MAX = 6000  # emergency brake only — sized so a 400–600-word decode always renders whole


def render_decode(dec):
    """The stranger's decode, whole — never cut silently: the agents read a mid-word stop
    as decoder data-loss and legislate against it. A bare [:400] slice here became a
    phantom '~100-token decoder limit' (t133-t137) and two of four live rules were built
    to dodge a bug that never existed. If it must elide, say so in the text."""
    if len(dec) <= DECODE_VIEW_MAX:
        return dec
    return (f"{dec[:DECODE_VIEW_MAX]}\n[VIEW ELIDED — this display is hiding "
            f"{len(dec) - DECODE_VIEW_MAX} further chars from you. The decode itself was "
            f"NOT truncated; it arrived complete. Judge fidelity by the grader score, "
            f"never by where this view stops.]")


def render_window(conv):
    out = []
    for e in conv[-WINDOW:]:
        if e["type"] == "measure":
            out.append(f"[turn {e['turn']} — MEASUREMENT] \"{e['text']}\" = {e['tokens']} tokens (exact)")
            continue
        if e["type"] == "notice":
            out.append(f"[turn {e['turn']} — HARNESS CORRECTION]\n{e['content']}")
            continue
        if e["type"] == "test":
            audit = ""
            if e.get("total"):
                bits = [f"answer key: {e.get('survived')}/{e['total']} items survived"]
                for lab in ("corrupted", "missing", "invented"):
                    if e.get(lab):
                        bits.append(f"{lab}: " + "; ".join(str(x) for x in e[lab][:4]))
                audit = "\n" + " | ".join(bits)
            ctl = ""
            if e.get("control_tokens"):
                cd = round((e["control_tokens"] - e["orig_tokens"]) / e["orig_tokens"] * 100)
                ctl = (f"\nCONTROL: a mindless script (lowercase, strip punctuation+articles) compressed "
                       f"this same message to {e['control_tokens']} tokens ({cd:+d}%). Savings below that "
                       f"line are free; only savings beyond it are language.")
            out.append(
                f"[turn {e['turn']} — LIVE TEST | payload: {e['payload']}]\n"
                f"original {e['orig_tokens']} tokens -> encoded {e['enc_tokens']} tokens "
                f"({e['token_delta_pct']:+d}%) | decode fidelity {e['fidelity']}/100" + ctl + "\n"
                f"encoded: {e['encoded']}\n"
                f"fresh decoder returned: {render_decode(e['decoded'])}\n"
                f"grader: {e['lost']}" + audit)
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


def econ_line(rb):
    """Live economics for the agents' STATE block, computed from the control's own data —
    numbers in the standing prompt go stale; these never do. Empty string on any problem."""
    try:
        p = json.loads((STATE / "probe.json").read_text())
        ex = [e for e in p["exams"] if e.get("fidelity", -1) >= 90 and e.get("orig_tokens")]
        last = ex[-10:]
        if len(last) < 3:
            return ""
        n = len(last)
        lang = sum(-(e["enc_tokens"] - e["orig_tokens"]) / e["orig_tokens"] * 100 for e in last) / n
        mini = sum(-(e["min_tokens"] - e["orig_tokens"]) / e["orig_tokens"] * 100 for e in last) / n
        saved = sum(e["orig_tokens"] - e["enc_tokens"] for e in last) / n
        k = rb.get("kernel_tokens", 0)
        be = (f"break-even for a stranger: {int(k / saved) + 1} messages" if saved > 0
              else "break-even for a stranger: never at current savings")
        return (f"\nECONOMICS (live, last {n} passing exams): entry fee = rulebook a stranger must "
                f"learn: {k} tokens | avg saved per message: {saved:+.0f} tokens | {be} | "
                f"you {lang:+.0f}% vs mindless script {mini:+.0f}%")
    except Exception:
        return ""


def agent_turn(conv, rb, meta, turn):
    agent = "B" if meta.get("last_agent") == "A" else "A"
    meta["last_agent"] = agent
    model = MODEL_A if agent == "A" else MODEL_B
    prompt = (ROOT / "prompts" / f"agent_{agent.lower()}.md").read_text()
    system = (f"{prompt}\n\n=== CURRENT RULEBOOK ===\n{render_rulebook(rb)}\n"
              f"=== STATE ===\nturn {turn} | next live test at turn "
              f"{((turn // TEST_EVERY) + 1) * TEST_EVERY}" + econ_line(rb))
    user = render_window(conv) + f"\n\nIt is turn {turn}. You are Agent {agent}. Respond."
    text, usage = call(model, system, user, max_tokens=2000, temperature=AGENT_TEMP, meta=meta)
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
        raw, _ = call(MODEL_A, prompt, "Write the message now.",
                      max_tokens=2000, temperature=1.0, meta=meta)
        text, _, keyblock = raw.strip().strip('"').partition("===KEY===")
        text = text.strip().strip('"').strip()
        # the answer key is born with the exam, blind to everything downstream —
        # grading checks receipts against it instead of forming one holistic opinion
        key = [l.strip() for l in keyblock.strip().splitlines() if l.strip()]
        if 200 <= len(text) <= 5000 and len(key) >= 6:
            return f"gen-{kind}-{domain.split()[0]}", text, key
    return None, None, None


def test_turn(conv, rb, meta, turn):
    pname, payload, key = gen_payload(meta)
    if payload is None:  # generator failed twice — fall back to the fixed battery (no key: holistic grading)
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
    encoded, _ = call(MODEL_A, enc_sys, payload, max_tokens=4000, temperature=0.3, meta=meta)
    dec_sys = ("You are a fresh agent. You have never seen any prior conversation. Below is the "
               "complete rulebook of a constructed language. Decode the message you receive: "
               "reconstruct the original content as faithfully as you can. Do not invent anything "
               "the message does not encode. Output ONLY the reconstruction.\n\n" + rbook)
    decoded, _ = call(MODEL_DECODER, dec_sys, encoded.strip(), max_tokens=4000, temperature=0.1, meta=meta)
    grade_sys = (ROOT / "prompts" / ("grader.md" if key else "grader_holistic.md")).read_text()
    if key:
        key_txt = "\n".join(f"{i + 1}. {k}" for i, k in enumerate(key))
        grade_user = f"ORIGINAL:\n{payload}\n\nANSWER KEY:\n{key_txt}\n\nDECODED:\n{decoded.strip()}"
    else:
        grade_user = f"ORIGINAL:\n{payload}\n\nDECODED:\n{decoded.strip()}"
    graded, _ = call(MODEL_GRADER, grade_sys, grade_user, max_tokens=1200, temperature=0, meta=meta)
    gm = re.search(r"\{.*\}", graded, re.S)
    try:
        g = json.loads(gm.group(0)) if gm else {}
    except json.JSONDecodeError:
        g = {}
    lost = str(g.get("lost", "grader output unparseable"))[:300]
    audit = {}
    if key:
        items = g.get("items", [])
        survived = sum(1 for i in items if i.get("verdict") == "SURVIVED")
        invented = g.get("invented", [])
        # the model classifies each item; the arithmetic is ours. inventions count as
        # extra failed items, keeping "invention penalized exactly like loss".
        fidelity = round(100 * survived / (len(key) + len(invented))) if items else -1
        if g.get("mode") == "RESPONDED" and fidelity >= 0:
            fidelity = min(fidelity, 15)  # decoder did the task instead of relaying it
        fidelity = max(0, min(100, fidelity)) if fidelity >= 0 else -1
        audit = {"key": key, "survived": survived, "total": len(key),
                 "corrupted": [f"{i.get('n')}: {i.get('note', '')}" for i in items if i.get("verdict") == "CORRUPTED"],
                 "missing": [f"{i.get('n')}: {i.get('note', '')}" for i in items if i.get("verdict") == "MISSING"],
                 "invented": invented}
    else:
        fidelity = max(0, min(100, int(g.get("fidelity", -1)))) if g.get("fidelity") is not None else -1
    orig_t = token_count(payload, meta)
    enc_t = token_count(encoded.strip(), meta)
    delta = round((enc_t - orig_t) / orig_t * 100)
    control_t = token_count(minify(payload), meta)  # the dumb-script floor, shown to the agents
    meta["tests_run"] = meta.get("tests_run", 0) + 1
    event = {"turn": turn, "agent": "harness", "type": "test", "payload": pname,
             "original": payload, "orig_tokens": orig_t, "enc_tokens": enc_t,
             "token_delta_pct": delta, "fidelity": fidelity, "lost": lost,
             "control_tokens": control_t,
             "encoded": encoded.strip(), "decoded": decoded.strip(), "tokens": enc_t,
             "decoder_model": MODEL_DECODER}
    event.update(audit)
    conv.append(event)
    for r in rb["rules"]:
        if r["status"] in ("proposed", "adopted"):
            r["scores"] = {"token_delta_pct": delta, "fidelity_pct": fidelity}
            r["history"].append(f"tested turn {turn}: fid {fidelity}, {delta:+d}%")
    print(f"[t{turn} TEST] {pname}  {orig_t}->{enc_t}tok ({delta:+d}%)  fid {fidelity}  "
          f"${meta['spend_usd']:.3f}", flush=True)


def consume_notice(conv, turn):
    """Notice inbox: if state/pending-notice.txt exists, deliver it as a harness notice
    this turn and remove the file. Lets notices travel via git without racing the
    VPS's own state commits (a direct conversation.json edit would)."""
    f = STATE / "pending-notice.txt"
    if not f.exists():
        return
    text = f.read_text().strip()
    if text:
        conv.append({"turn": turn, "agent": "harness", "type": "notice", "content": text})
        print(f"[t{turn} NOTICE] delivered ({len(text)} chars)", flush=True)
    f.unlink()


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
        consume_notice(conv, turn)
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
