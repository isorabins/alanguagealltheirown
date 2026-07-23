#!/usr/bin/env python3
"""A Language All Their Own — the entire engine.

Two agents negotiate an AI-to-AI language; every rule survives (or dies by)
an encode/decode test against a fresh decoder. This file is deliberately all
the code there is: plumbing only, the LLMs do the language.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from collaboration import (deliver_one, empty_state, import_inbox_spool, public_state,
                           stable_record, write_outbox)
from conversation_exam import run_conversation
from rulebook import (apply_authorized_motion, language_payload, render_language,
                      render_legislature, score_judgment, motion_line)
from state_store import atomic_write_json, load_json

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_A = "deepseek/deepseek-v3.2"
MODEL_B = "moonshotai/kimi-k2.6"
MODEL_DECODER = "moonshotai/kimi-k2.6"  # a FOREIGN decoder: the stranger must not share the negotiators' weights
MODEL_GRADER = "deepseek/deepseek-v3.2"
PRICE_IN = 0.2145 / 1e6   # $/token, OpenRouter listing 2026-07-14
PRICE_OUT = 0.32175 / 1e6
WEB_SEARCH_PRICE = 0.005

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
    return load_json(STATE / name, default)


def save(name, obj):
    atomic_write_json(STATE / name, obj)


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
    """Compatibility name for the only ordinary language boundary: adopted rules."""
    return render_language(rb)


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
            score = (f"decode fidelity {e['fidelity']}/100" if e.get("fidelity") is not None
                     else f"no valid score ({e.get('judge_reason', 'invalid')})")
            out.append(
                f"[turn {e['turn']} — LIVE TEST | payload: {e['payload']}]\n"
                f"original {e['orig_tokens']} tokens -> encoded {e['enc_tokens']} tokens "
                f"({e['token_delta_pct']:+d}%) | {score}\n"
                f"encoded: {e['encoded']}\n"
                f"fresh decoder returned: {render_decode(e['decoded'])}\n"
                f"grader: {e['lost']}" + audit)
        else:
            out.append(f"[turn {e['turn']}] AGENT {e['agent']}:\n{e['content']}")
    return "\n\n".join(out) if out else "(no conversation yet — the rulebook is empty and you speak first)"


def rationale_for(text, line):
    """The paragraph around the exact matched motion line, minus verb lines — the 'why'."""
    paras = text.split("\n\n")
    idx = next((i for i, p in enumerate(paras) if line in p), 0)
    for cand in (paras[idx], paras[idx - 1] if idx else ""):
        why = " ".join(l for l in cand.splitlines()
                       if not re.match(r"\s*\**(PROPOSE|REPEAL|ADOPT|REJECT|REVISE|REQUEST(?:-REVISION|-TEST)?)", l)).strip()
        if len(why) > 20:
            return why[:280]
    return ""


def write_viewer_state(conv, rb, meta, collaboration=None, conversations=None):
    (ROOT / "viewer" / "state.js").write_text(
        "window.STATE = " + json.dumps(
            {"conversation": conv, "rulebook": rb,
             "collaboration": public_state(collaboration or empty_state()),
             "conversations": conversations or [],
             "meta": {"spend_usd": meta.get("spend_usd", 0), "model": MODEL_A,
                      "updated": now_iso(), "run": meta.get("run", "local")}}) + ";\n")


def agent_turn(conv, rb, meta, collaboration, turn):
    agent = "B" if meta.get("last_agent") == "A" else "A"
    meta["last_agent"] = agent
    model = MODEL_A if agent == "A" else MODEL_B
    prompt = (ROOT / "prompts" / f"agent_{agent.lower()}.md").read_text()
    constitution = (ROOT / "prompts" / "constitution.md").read_text()
    delivery = (deliver_one(collaboration, "RESEARCH", agent, turn) or
                deliver_one(collaboration, "ASK", agent, turn) or
                deliver_one(collaboration, "SUGGESTION", agent, turn))
    delivered = ""
    if delivery:
        delivered = "\n\n=== BOUNDED COLLABORATION INPUT ===\n" + json.dumps(delivery, ensure_ascii=False)
    system = (f"{constitution}\n\n{prompt}\n\n=== ADOPTED LANGUAGE ===\n{render_language(rb)}\n"
              f"\n=== LEGISLATURE ===\n{render_legislature(rb)}\n"
              f"=== STATE ===\nturn {turn} | next live test at turn "
              f"{((turn // TEST_EVERY) + 1) * TEST_EVERY}" + delivered)
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
    matched_line = motion_line(text)
    receipt = apply_authorized_motion(text, rb, turn, agent,
                                      rationale_for(text, matched_line) if matched_line else "")
    conv.append({"turn": turn, "agent": "harness", "type": "legislature",
                 "motion_receipt": receipt.dict()})
    if receipt.changed:
        rb["version"] = f"0.{rb['changes'] + 1}"
        rb["changes"] += 1
        rb["kernel_tokens"] = token_count(render_language(rb), meta)
    if delivery and delivery.get("kind") == "SUGGESTION":
        suggestion = next((row for row in collaboration.get("suggestions", [])
                           if row.get("id") == delivery.get("id")), None)
        if suggestion:
            suggestion["status"] = "acted" if receipt.changed else "no_action"
            suggestion["outcome"] = receipt.reason
            suggestion["outcome_turn"] = turn
    for kind in ("RESEARCH", "ASK"):
        match = re.search(rf"^\s*{kind}\s*:\s*(.+)$", text, re.M)
        if match:
            record_id = f"{kind.lower()}-{turn}-{agent.lower()}"
            bucket = "research" if kind == "RESEARCH" else "asks"
            if not any(r.get("id") == record_id for r in collaboration[bucket]):
                record = stable_record(kind, agent, match.group(1), record_id)
                record["request_turn"] = turn
                collaboration[bucket].append(record)
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
        key = normalize_answer_key(keyblock)
        if 200 <= len(text) <= 5000 and len(key) >= 6:
            return f"gen-{kind}-{domain.split()[0]}", text, key
    return None, None, None


def normalize_answer_key(raw):
    lines = raw if isinstance(raw, list) else str(raw).splitlines()
    return [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()
            for line in lines
            if re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", str(line)).strip()]


def extract_answer_key(payload, meta):
    """Create the fixed exam key before encoding; failure makes the score invalid."""
    prompt = (ROOT / "prompts" / "answer_key.md").read_text()
    raw, _ = call(MODEL_GRADER, prompt, payload, max_tokens=1200, temperature=0, meta=meta)
    match = re.search(r"\[.*\]", raw, re.S)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return normalize_answer_key(parsed)
        except json.JSONDecodeError:
            pass
    return []


def test_turn(conv, rb, meta, turn):
    pname, payload, key = gen_payload(meta)
    if payload is None:  # generator failed twice — key the fixed payload before either agent sees it
        by_kind = {}
        for f in sorted((ROOT / "payloads").glob("*.txt")):
            by_kind.setdefault(f.name.split("-")[0], []).append(f)
        kinds = sorted(by_kind)  # interleave prose/task/data so no type dominates
        payloads = [ks[i] for i in range(max(len(v) for v in by_kind.values()))
                    for ks in (by_kind[k] for k in kinds) if i < len(ks)]
        p = payloads[meta.get("tests_run", 0) % len(payloads)]
        pname, payload = p.name, p.read_text().strip()
        key = extract_answer_key(payload, meta)
    captured = language_payload(rb)
    rbook = render_language(rb)
    enc_sys = ("You are the encoder. Encode the message below into the project language "
               "using ONLY this rulebook. Where the rulebook is silent, fall back to plain "
               "English for that part. Output ONLY the encoded message, nothing else.\n\n" + rbook)
    encoded, _ = call(MODEL_A, enc_sys, payload, max_tokens=4000, temperature=0.3, meta=meta)
    dec_sys = ("You are a fresh agent. You have never seen any prior conversation. Below is the "
               "complete rulebook of a constructed language. Decode the message you receive: "
               "reconstruct the original content as faithfully as you can. Do not invent anything "
               "the message does not encode. Output ONLY the reconstruction.\n\n" + rbook)
    decoded, _ = call(MODEL_DECODER, dec_sys, encoded.strip(), max_tokens=4000, temperature=0.1, meta=meta)
    grade_sys = (ROOT / "prompts" / "grader.md").read_text()
    if key:
        key_txt = "\n".join(f"{i + 1}. {k}" for i, k in enumerate(key))
        grade_user = f"ORIGINAL:\n{payload}\n\nANSWER KEY:\n{key_txt}\n\nDECODED:\n{decoded.strip()}"
        graded, _ = call(MODEL_GRADER, grade_sys, grade_user, max_tokens=1200, temperature=0, meta=meta)
        gm = re.search(r"\{.*\}", graded, re.S)
        try:
            g = json.loads(gm.group(0)) if gm else {}
        except json.JSONDecodeError:
            g = {}
    else:
        g = {}
    lost = str(g.get("lost", "answer key unavailable" if not key else "grader output unparseable"))[:300]
    audit = {}
    if key:
        scored = score_judgment(key, g)
        items = g.get("items", []) if scored["valid"] else []
        fidelity = scored["fidelity"]
        audit = {"key": key, "judge_valid": scored["valid"], "judge_reason": scored["reason"],
                 "survived": scored.get("survived", 0), "total": len(key),
                 "corrupted": [f"{i.get('n')}: {i.get('note', '')}" for i in items if i.get("verdict") == "CORRUPTED"],
                 "missing": [f"{i.get('n')}: {i.get('note', '')}" for i in items if i.get("verdict") == "MISSING"],
                 "invented": scored.get("invented", [])}
        if not scored["valid"]:
            lost = f"invalid judge output: {scored['reason']}"
    else:
        fidelity = None
        audit = {"key": [], "judge_valid": False, "judge_reason": "answer_key_unavailable",
                 "survived": 0, "total": 0, "corrupted": [], "missing": [], "invented": []}
    orig_t = token_count(payload, meta)
    enc_t = token_count(encoded.strip(), meta)
    delta = round((enc_t - orig_t) / orig_t * 100)
    meta["tests_run"] = meta.get("tests_run", 0) + 1
    event = {"turn": turn, "agent": "harness", "type": "test", "payload": pname,
             "original": payload, "orig_tokens": orig_t, "enc_tokens": enc_t,
             "token_delta_pct": delta, "fidelity": fidelity, "lost": lost,
             "encoded": encoded.strip(), "decoded": decoded.strip(), "tokens": enc_t,
             "decoder_model": MODEL_DECODER, "language_version": captured["version"],
             "language_hash": captured["hash"]}
    event.update(audit)
    conv.append(event)
    exams = meta.setdefault("corpus_exams", [])
    exams.append({"turn": turn, "language_version": captured["version"],
                  "language_hash": captured["hash"], "fidelity": fidelity,
                  "token_delta_pct": delta, "valid": fidelity is not None})
    meta["corpus_exams"] = exams[-500:]
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


def process_one_research(collaboration, meta, turn):
    """Resolve at most the oldest queued request; evidence cannot alter rule state."""
    record = next((r for r in collaboration.get("research", []) if r.get("status") == "queued"), None)
    if not record:
        return
    record["status"] = "researching"
    spend_before = float(meta.get("spend_usd", 0.0))
    body = {"model": MODEL_A,
            "messages": [{"role": "system", "content": (ROOT / "prompts" / "research.md").read_text()},
                         {"role": "user", "content": record["question"]}],
            "tools": [{"type": "openrouter:web_search", "parameters": {"max_total_results": 5}}],
            "max_tokens": 1000, "temperature": 0}
    try:
        response = requests.post(API_URL, headers={"Authorization": f"Bearer {api_key()}",
                                                   "Content-Type": "application/json"},
                                 json=body, timeout=180)
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        usage = data.get("usage", {})
        usage = usage if isinstance(usage, dict) else {}
        tool_use = usage.get("server_tool_use", {})
        tool_use = tool_use if isinstance(tool_use, dict) else {}
        meta["spend_usd"] = round(
            meta.get("spend_usd", 0.0)
            + usage.get("prompt_tokens", 0) * PRICE_IN
            + usage.get("completion_tokens", 0) * PRICE_OUT
            + int(tool_use.get("web_search_requests", 0) or 0) * WEB_SEARCH_PRICE, 6)
        try:
            parsed = json.loads(message.get("content") or "{}")
        except json.JSONDecodeError:
            parsed = {"findings": message.get("content", ""), "limitations": "model returned non-JSON"}
        citations = []
        for annotation in message.get("annotations", []):
            citation = annotation.get("url_citation", {})
            if citation.get("url"):
                citations.append({"title": citation.get("title", citation["url"]), "url": citation["url"]})
        findings = str(parsed.get("findings", "")).strip()
        limitations = parsed.get("limitations", [])
        if isinstance(limitations, str):
            limitations = [limitations] if limitations.strip() else []
        if not isinstance(limitations, list):
            limitations = ["research response had malformed limitations"]
        resolved_citations = citations or parsed.get("citations", [])
        resolved_citations = resolved_citations if isinstance(resolved_citations, list) else []
        resolved_citations = [c for c in resolved_citations if isinstance(c, dict)
                              and isinstance(c.get("url"), str)
                              and c["url"].lower().startswith(("https://", "http://"))]
        no_evidence = not findings or not resolved_citations
        if no_evidence and not limitations:
            limitations = ["no usable cited evidence returned"]
        record.update({"status": "no_evidence" if no_evidence else "answered", "findings": findings,
                       "limitations": limitations, "citations": resolved_citations,
                       "no_evidence": no_evidence, "answer_turn": turn,
                       "usage": {"prompt_tokens": usage.get("prompt_tokens", 0),
                                 "completion_tokens": usage.get("completion_tokens", 0),
                                 "web_search_requests": int(tool_use.get("web_search_requests", 0) or 0)},
                       "cost_usd": round(float(meta.get("spend_usd", 0.0)) - spend_before, 6)})
    except Exception as exc:
        record.update({"status": "error", "findings": "", "citations": [], "no_evidence": True,
                       "limitations": [f"research unavailable: {exc.__class__.__name__}"],
                       "error": exc.__class__.__name__, "cost_usd": round(float(meta.get("spend_usd", 0.0)) - spend_before, 6),
                       "answer_turn": turn})


def maybe_run_conversation(rb, meta, turn, conversations):
    if not meta.get("tests_run") or meta["tests_run"] % 32 != 0:
        return
    if conversations and conversations[-1].get("ordinary_exam_count") == meta["tests_run"]:
        return
    scenario = {"prompt": "Plan a handoff of order AL-204: Mira packs 12 units by 15:00 UTC; Ken verifies count and ships by 16:00 UTC.",
                "requirements": ["Mira packs 12 units", "packing deadline is 15:00 UTC",
                                 "Ken verifies the count", "shipping deadline is 16:00 UTC"]}
    def speaker(speaker_name, language, user):
        prompt = (ROOT / "prompts" / "conversation.md").read_text() + "\n\n" + language
        model = MODEL_A if speaker_name == "A" else MODEL_B
        text, usage = call(model, prompt, user, max_tokens=500, temperature=0.3, meta=meta)
        return {"content": text, "model": model, "usage": usage}
    def judge(artifact):
        raw, usage = call(MODEL_GRADER, (ROOT / "prompts" / "conversation_judge.md").read_text(),
                          json.dumps(artifact), max_tokens=700, temperature=0, meta=meta)
        match = re.search(r"\{.*\}", raw, re.S)
        try:
            result = json.loads(match.group(0)) if match else {"valid": False, "summary": "unparseable"}
        except json.JSONDecodeError:
            result = {"valid": False, "summary": "unparseable"}
        result["_receipt"] = {"model": MODEL_GRADER, "usage": usage}
        return result
    artifact = run_conversation(rb, scenario, speaker, judge, turn,
                                models={"A": MODEL_A, "B": MODEL_B, "judge": MODEL_GRADER})
    artifact["ordinary_exam_count"] = meta["tests_run"]
    conversations.append(artifact)


def run(turns):
    STATE.mkdir(exist_ok=True)
    conv = load("conversation.json", [])
    rb = load("rulebook.json", {"version": "0.0", "kernel_tokens": 0, "changes": 0,
                                "next_id": 1, "rules": []})
    meta = load("meta.json", {"spend_usd": 0.0, "last_agent": None, "tests_run": 0,
                              "started": now_iso()})
    collaboration = load("collaboration.json", empty_state())
    conversations = load("conversations.json", [])
    start_turn = (conv[-1]["turn"] + 1) if conv else 1
    for turn in range(start_turn, start_turn + turns):
        if meta["spend_usd"] >= SPEND_CAP:
            print(f"SPEND CAP hit (${meta['spend_usd']:.2f}) — stopping.", flush=True)
            break
        consume_notice(conv, turn)
        collaboration = import_inbox_spool(
            collaboration, STATE / "collaboration-inbox.json", turn=turn)
        save("collaboration.json", collaboration)
        process_one_research(collaboration, meta, turn)
        if turn % TEST_EVERY == 0:
            test_turn(conv, rb, meta, turn)
            maybe_run_conversation(rb, meta, turn, conversations)
        else:
            agent_turn(conv, rb, meta, collaboration, turn)
        save("conversation.json", conv)
        save("rulebook.json", rb)
        save("meta.json", meta)
        save("collaboration.json", collaboration)
        write_outbox(STATE / "collaboration-outbox.json", collaboration)
        save("public-collaboration.json", public_state(collaboration))
        save("conversations.json", conversations)
        write_viewer_state(conv, rb, meta, collaboration, conversations)
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
