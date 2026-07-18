// Shared plumbing for the try-it-yourself exam endpoints.
// Written as Vercel-style Node functions; tryit/serve.js runs them locally.
// The one invariant of the whole piece holds here too: the decoder sees ONLY
// the rulebook and the encoded message. Never the original.
const fs = require("fs");
const path = require("path");

const API_URL = "https://openrouter.ai/api/v1/chat/completions";
const RAW = "https://raw.githubusercontent.com/isorabins/alanguagealltheirown/main/";
const MODEL_ENCODER = "deepseek/deepseek-v3.2";
const MODEL_DECODER = "moonshotai/kimi-k2.6";
const MODEL_GRADER = "deepseek/deepseek-v3.2";

const TEXT_MAX = 700;            // characters of user copy
const PER_IP_PER_HOUR = 6;
const GLOBAL_PER_DAY = 150;      // in-memory: resets on cold start; real KV before heavy traffic

let _key = null;
function apiKey() {
  if (_key) return _key;
  if (process.env.OPENROUTER_API_KEY) return (_key = process.env.OPENROUTER_API_KEY.trim());
  try {
    const env = fs.readFileSync(path.join(__dirname, "..", "..", ".env"), "utf8");
    for (const line of env.split("\n"))
      if (line.startsWith("OPENROUTER_API_KEY=")) return (_key = line.split("=", 2)[1].trim());
  } catch (e) { /* fall through */ }
  throw new Error("no OPENROUTER_API_KEY available");
}

let _noReasoning = false;
async function call(model, system, user, opts) {
  const o = opts || {};
  const messages = (system ? [{ role: "system", content: system }] : []).concat([{ role: "user", content: user }]);
  const body = { model, messages, max_tokens: o.maxTokens || 600, temperature: o.temperature == null ? 0.7 : o.temperature };
  if (model.startsWith("deepseek/")) body.provider = { order: ["deepseek"] }; // token accounting stays on one tokenizer
  if (!_noReasoning) body.reasoning = { enabled: false };
  const headers = {
    "Content-Type": "application/json",
    Authorization: "Bearer " + apiKey(),
    "HTTP-Referer": "https://alanguagealltheirown.com",
    "X-Title": "a-language-all-their-own-tryit",
  };
  const delays = [0, 3000, 8000, 20000];
  for (let i = 0; i < delays.length; i++) {
    if (delays[i]) await new Promise((r) => setTimeout(r, delays[i]));
    let r;
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 120000);
      r = await fetch(API_URL, { method: "POST", headers, body: JSON.stringify(body), signal: ctl.signal });
      clearTimeout(t);
    } catch (e) { continue; }
    if (r.status === 400 && !_noReasoning) { _noReasoning = true; delete body.reasoning; continue; }
    if ([429, 500, 502, 503, 520, 524].includes(r.status)) continue;
    if (!r.ok) throw new Error("api " + r.status);
    const d = await r.json();
    if (d.error) continue;
    return { text: (d.choices && d.choices[0].message.content) || "", usage: d.usage || {} };
  }
  throw new Error("api: retries exhausted");
}

let _overhead = null;
async function tokenCount(text) {
  // loop.py's exact method: probe call, prompt_tokens minus calibrated overhead
  if (_overhead == null) {
    const u = await call(MODEL_GRADER, null, "x", { maxTokens: 1, temperature: 0 });
    _overhead = (u.usage.prompt_tokens || 1) - 1;
  }
  const u = await call(MODEL_GRADER, null, text, { maxTokens: 1, temperature: 0 });
  return Math.max(1, (u.usage.prompt_tokens || 1) - _overhead);
}

let _rb = null, _rbAt = 0;
async function getRulebook() {
  if (_rb && Date.now() - _rbAt < 5 * 60 * 1000) return _rb;
  const r = await fetch(RAW + "state/rulebook.json", { cache: "no-store" });
  if (!r.ok) throw new Error("rulebook fetch " + r.status);
  _rb = await r.json();
  _rbAt = Date.now();
  return _rb;
}

function renderRulebook(rb) {
  // faithful port of loop.py render_rulebook — the exam context must be identical
  if (!rb.rules || !rb.rules.length) return "The rulebook is empty. No rules exist yet.";
  const lines = ["RULEBOOK v" + rb.version + " — " + rb.kernel_tokens + " tokens of context, every message pays for it"];
  for (const r of rb.rules) {
    const s = r.scores;
    if (r.status === "rejected" || r.status === "reverted") {
      let died = "?";
      for (let i = r.history.length - 1; i >= 0; i--) {
        const e = r.history[i];
        if (e && typeof e === "object" && (e.verb === "reject" || e.verb === "rejected")) { died = e.turn; break; }
      }
      const stub = r.text_en.slice(0, 60).trimEnd() + (r.text_en.length > 60 ? "…" : "");
      const kill = s ? ` — died at fidelity ${s.fidelity_pct}, ${s.token_delta_pct >= 0 ? "+" : ""}${s.token_delta_pct}%` : "";
      lines.push(`${r.id} [${r.status} t${died}] ${stub}${kill}`);
      continue;
    }
    const score = s ? ` (last test: fidelity ${s.fidelity_pct}, tokens ${s.token_delta_pct >= 0 ? "+" : ""}${s.token_delta_pct}%)` : "";
    lines.push(`${r.id} [${r.status}] ${r.text_en}${score}`);
  }
  return lines.join("\n");
}

let _grader = null, _graderAt = 0;
async function getGraderPrompt() {
  if (_grader && Date.now() - _graderAt < 30 * 60 * 1000) return _grader;
  const r = await fetch(RAW + "prompts/grader.md", { cache: "no-store" });
  if (!r.ok) throw new Error("grader prompt fetch " + r.status);
  _grader = await r.text();
  _graderAt = Date.now();
  return _grader;
}

const _ipHits = new Map();
let _daySpent = 0, _dayStart = Date.now();
function guard(req, res, field, maxLen) {
  if (req.method !== "POST") { res.status(405).json({ error: "POST only" }); return null; }
  if (Date.now() - _dayStart > 86400000) { _daySpent = 0; _dayStart = Date.now(); }
  if (_daySpent >= GLOBAL_PER_DAY) { res.status(429).json({ error: "the exam room is full for today — come back tomorrow" }); return null; }
  const ip = String(req.headers["x-forwarded-for"] || (req.socket && req.socket.remoteAddress) || "?").split(",")[0].trim();
  const now = Date.now();
  const hits = (_ipHits.get(ip) || []).filter((t) => now - t < 3600000);
  if (hits.length >= PER_IP_PER_HOUR) { res.status(429).json({ error: "rate limit: a few runs per hour per visitor" }); return null; }
  const val = req.body && req.body[field];
  if (typeof val !== "string" || !val.trim()) { res.status(400).json({ error: "missing " + field }); return null; }
  if (val.length > maxLen) { res.status(400).json({ error: field + " too long (max " + maxLen + " chars)" }); return null; }
  hits.push(now);
  _ipHits.set(ip, hits);
  _daySpent++;
  return val.trim();
}

module.exports = { call, tokenCount, getRulebook, renderRulebook, getGraderPrompt, guard,
  MODEL_ENCODER, MODEL_DECODER, MODEL_GRADER, TEXT_MAX };
