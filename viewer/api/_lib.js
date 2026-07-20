const crypto = require("crypto");

const API_URL = "https://openrouter.ai/api/v1/chat/completions";
const RAW = "https://raw.githubusercontent.com/isorabins/alanguagealltheirown/main/";
const MODEL_ENCODER = "deepseek/deepseek-v3.2";
const MODEL_DECODER = "moonshotai/kimi-k2.6";
const MODEL_GRADER = "deepseek/deepseek-v3.2";
const TEXT_MAX = 700;
const PER_IP_PER_HOUR = 6;
const GLOBAL_PER_DAY = 150;

class ProviderError extends Error {
  constructor(code, message, status) { super(message); this.code = code; this.status = status || 502; }
}

function apiKey() {
  const key = String(process.env.OPENROUTER_PUBLIC_API_KEY || "").trim();
  if (!key) throw new ProviderError("public_key_unavailable", "public Try It is not configured", 503);
  return key;
}

function classifyProvider(status, data) {
  const message = String((data && data.error && (data.error.message || data.error)) || "").toLowerCase();
  const metadata = data && data.error && data.error.metadata;
  if (status === 402 || (status === 429 && metadata && metadata.limit_reset === "monthly") ||
      /monthly.+(limit|allowance)|limit.+monthly|insufficient credits/.test(message)) {
    return "allowance_exhausted";
  }
  if (status === 401 || status === 403) return "provider_auth_error";
  if (status === 429) return "provider_rate_limited";
  if (status >= 500) return "provider_unavailable";
  return "provider_error";
}

let noReasoning = false;
async function call(model, system, user, opts) {
  const o = opts || {};
  const messages = (system ? [{ role: "system", content: system }] : []).concat([{ role: "user", content: user }]);
  const body = { model, messages, max_tokens: o.maxTokens || 600,
    temperature: o.temperature == null ? 0.7 : o.temperature };
  if (model.startsWith("deepseek/")) body.provider = { order: ["deepseek"] };
  if (!noReasoning) body.reasoning = { enabled: false };
  const headers = { "Content-Type": "application/json", Authorization: "Bearer " + apiKey(),
    "HTTP-Referer": "https://alanguagealltheirown.com", "X-Title": "a-language-all-their-own-tryit" };
  const delays = o.noRetry ? [0] : [0, 250, 750];
  let last = new ProviderError("provider_unavailable", "public model provider did not respond", 503);
  for (const delay of delays) {
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
    let response;
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), o.timeoutMs || 30000);
      response = await fetch(API_URL, { method: "POST", headers, body: JSON.stringify(body), signal: controller.signal });
      clearTimeout(timeout);
    } catch (error) {
      last = new ProviderError("provider_network_error", "public model provider could not be reached", 503);
      continue;
    }
    let data = {};
    try { data = await response.json(); } catch (_) { data = {}; }
    if (response.status === 400 && !noReasoning && /reason/i.test(JSON.stringify(data))) {
      noReasoning = true; delete body.reasoning; continue;
    }
    if (!response.ok || data.error) {
      const code = classifyProvider(response.status, data);
      last = new ProviderError(code, code === "allowance_exhausted" ?
        "the public monthly allowance is exhausted; it reopens after the monthly UTC reset" :
        "public model provider failed", code === "allowance_exhausted" ? 429 : 502);
      if (!["provider_unavailable", "provider_rate_limited"].includes(code)) throw last;
      continue;
    }
    const text = data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
    if (!text) throw new ProviderError("provider_empty_response", "provider returned no text", 502);
    return { text, usage: data.usage || {} };
  }
  throw last;
}

let overhead = null;
async function tokenCount(text) {
  if (overhead == null) {
    const probe = await call(MODEL_GRADER, null, "x", { maxTokens: 1, temperature: 0 });
    overhead = (probe.usage.prompt_tokens || 1) - 1;
  }
  const result = await call(MODEL_GRADER, null, text, { maxTokens: 1, temperature: 0 });
  return Math.max(1, (result.usage.prompt_tokens || 1) - overhead);
}

let cachedRulebook = null, cachedAt = 0;
async function getRulebook(force) {
  if (!force && cachedRulebook && Date.now() - cachedAt < 300000) return cachedRulebook;
  const response = await fetch(RAW + "state/rulebook.json", { cache: "no-store" });
  if (!response.ok) throw new ProviderError("rulebook_unavailable", "current rulebook could not be loaded", 503);
  cachedRulebook = await response.json(); cachedAt = Date.now();
  return cachedRulebook;
}

function languagePayload(rulebook) {
  const rules = (rulebook.rules || []).filter((rule) => rule.status === "adopted")
    .map((rule) => ({ id: rule.id, text_en: rule.text_en }));
  const canonical = JSON.stringify({ rules });
  const hash = crypto.createHash("sha256").update(canonical + "\n").digest("hex");
  return { rules, hash, version: "adopted-" + hash.slice(0, 12) };
}

function renderRulebook(rulebook) {
  const view = languagePayload(rulebook);
  if (!view.rules.length) return `LANGUAGE ${view.version}\nNo adopted rules. Use plain English.`;
  return [`LANGUAGE ${view.version} (${view.rules.length} adopted rules)`]
    .concat(view.rules.map((rule) => `${rule.id}: ${rule.text_en}`)).join("\n");
}

let graderPrompt = null;
async function getGraderPrompt() {
  if (graderPrompt) return graderPrompt;
  const response = await fetch(RAW + "prompts/grader.md", { cache: "no-store" });
  if (!response.ok) throw new ProviderError("grader_unavailable", "grader contract could not be loaded", 503);
  graderPrompt = await response.text(); return graderPrompt;
}

const ipHits = new Map();
let daySpent = 0, dayStart = Date.now();
function guard(req, res, field, maxLen) {
  if (req.method !== "POST") { res.status(405).json({ error: "POST only", code: "method_not_allowed" }); return null; }
  if (Date.now() - dayStart > 86400000) { daySpent = 0; dayStart = Date.now(); }
  if (daySpent >= GLOBAL_PER_DAY) { res.status(429).json({ error: "public daily request boundary reached", code: "daily_boundary" }); return null; }
  const ip = String(req.headers["x-forwarded-for"] || (req.socket && req.socket.remoteAddress) || "?").split(",")[0].trim();
  const now = Date.now(); const hits = (ipHits.get(ip) || []).filter((at) => now - at < 3600000);
  if (hits.length >= PER_IP_PER_HOUR) { res.status(429).json({ error: "visitor rate limit reached", code: "rate_limited" }); return null; }
  const value = req.body && req.body[field];
  if (typeof value !== "string" || !value.trim()) { res.status(400).json({ error: "missing " + field, code: "invalid_input" }); return null; }
  if (value.length > maxLen) { res.status(400).json({ error: field + " too long", code: "invalid_input" }); return null; }
  hits.push(now); ipHits.set(ip, hits); daySpent += 1; return value.trim();
}

function requireJson(req, res) {
  if (!/^application\/json(?:\s*;|$)/i.test(String(req.headers["content-type"] || ""))) {
    res.status(415).json({ error: "application/json required", code: "invalid_content_type" }); return false;
  }
  return true;
}

function sendError(res, error, prefix) {
  const code = error.code || "internal_error"; const status = error.status || 500;
  res.status(status).json({ error: prefix ? prefix + ": " + error.message : error.message, code });
}

module.exports = { call, tokenCount, getRulebook, languagePayload, renderRulebook, getGraderPrompt,
  guard, requireJson, classifyProvider, sendError, ProviderError, MODEL_ENCODER, MODEL_DECODER, MODEL_GRADER, TEXT_MAX };
