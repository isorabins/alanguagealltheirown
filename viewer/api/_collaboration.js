const crypto = require("crypto");

const NAMESPACE = "alato:v1";
const SESSION_SECONDS = 30 * 60;
const CLEANUP_REVIEW = "https://raw.githubusercontent.com/isorabins/alanguagealltheirown/main/specs/001-experiment-repair/evidence/cleanup-live/review.json";

function config() {
  const url = String(process.env.UPSTASH_REDIS_REST_URL || "").replace(/\/$/, "");
  const token = String(process.env.UPSTASH_REDIS_REST_TOKEN || "");
  if (!url || !token) throw Object.assign(new Error("collaboration store unavailable"), { status: 503, code: "store_unavailable" });
  return { url, token };
}

async function command(...parts) {
  const { url, token } = config();
  const response = await fetch(url, { method: "POST", headers: { Authorization: "Bearer " + token,
    "Content-Type": "application/json" }, body: JSON.stringify(parts) });
  let data = {}; try { data = await response.json(); } catch (_) {}
  if (!response.ok || data.error) throw Object.assign(new Error("collaboration store command failed"),
    { status: 503, code: "store_unavailable" });
  return data.result;
}

function cleanText(value, max) {
  if (typeof value !== "string") throw Object.assign(new Error("text is required"), { status: 400, code: "invalid_input" });
  const clean = value.replace(/\r\n?/g, "\n").trim();
  if (!clean || clean.length > max) throw Object.assign(new Error("text must contain 1-" + max + " characters"),
    { status: 400, code: "invalid_input" });
  return clean;
}

function requireJson(req) {
  if (!/^application\/json(?:\s*;|$)/i.test(String(req.headers["content-type"] || ""))) {
    throw Object.assign(new Error("application/json required"), { status: 415, code: "invalid_content_type" });
  }
}

function recordId(kind, idempotencyKey) {
  const key = cleanText(idempotencyKey, 160);
  return kind.toLowerCase() + "-" + crypto.createHash("sha256").update(key).digest("hex").slice(0, 32);
}

async function enqueue(kind, record, idempotencyKey) {
  const id = recordId(kind, idempotencyKey);
  const value = JSON.stringify({ ...record, id, kind, created_at: Date.now() });
  const script = "if redis.call('SET',KEYS[1],'1','NX') then redis.call('RPUSH',KEYS[2],ARGV[1]); return 1 else return 0 end";
  const created = await command("EVAL", script, 2, `${NAMESPACE}:id:${id}`, `${NAMESPACE}:queue:${kind.toLowerCase()}`, value);
  return { id, created: Number(created) === 1 };
}

async function existingEnqueue(kind, idempotencyKey) {
  const id = recordId(kind, idempotencyKey);
  const exists = await command("EXISTS", `${NAMESPACE}:id:${id}`);
  return Number(exists) > 0 ? { id, created: false } : null;
}

async function reserveAction(target, value) {
  const fingerprint = crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
  const key = `${NAMESPACE}:action-target:${recordId("TARGET", target)}`;
  const created = await command("SET", key, fingerprint, "NX", "EX", 86400);
  if (created) return true;
  return await command("GET", key) === fingerprint;
}

function cookies(req) {
  const result = {};
  for (const part of String(req.headers.cookie || "").split(";")) {
    const index = part.indexOf("="); if (index < 0) continue;
    const key = part.slice(0, index).trim();
    try { result[key] = decodeURIComponent(part.slice(index + 1)); } catch (_) {}
  }
  return result;
}

function sessionKey(token) {
  return `${NAMESPACE}:session:${crypto.createHash("sha256").update(token).digest("hex")}`;
}

async function session(req) {
  const token = cookies(req).alato_human;
  if (!token || !/^[a-f0-9]{64}$/.test(token)) return null;
  const raw = await command("GET", sessionKey(token));
  if (!raw) return null;
  const parsed = JSON.parse(raw);
  return parsed.expires_at > Date.now() ? parsed : null;
}

async function requireSession(req) {
  const current = await session(req);
  if (!current) throw Object.assign(new Error("human session required"), { status: 401, code: "unauthorized" });
  return current;
}

async function login(password) {
  const expected = String(process.env.HUMAN_PASSWORD || "");
  if (!expected) throw Object.assign(new Error("human login unavailable"), { status: 503, code: "not_configured" });
  const supplied = crypto.createHash("sha256").update(String(password || "")).digest();
  const target = crypto.createHash("sha256").update(expected).digest();
  if (!crypto.timingSafeEqual(supplied, target)) {
    throw Object.assign(new Error("authentication failed"), { status: 401, code: "unauthorized" });
  }
  const token = crypto.randomBytes(32).toString("hex");
  const value = JSON.stringify({ created_at: Date.now(), expires_at: Date.now() + SESSION_SECONDS * 1000 });
  await command("SET", sessionKey(token), value, "EX", SESSION_SECONDS, "NX");
  return { token, expires_at: JSON.parse(value).expires_at };
}

function setSessionCookie(res, token) {
  res.setHeader("Set-Cookie", `alato_human=${encodeURIComponent(token)}; Max-Age=${SESSION_SECONDS}; Path=/; HttpOnly; Secure; SameSite=Strict`);
}

function clearSessionCookie(res) {
  res.setHeader("Set-Cookie", "alato_human=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Strict");
}

async function logout(req, res) {
  const token = cookies(req).alato_human;
  if (token && /^[a-f0-9]{64}$/.test(token)) await command("DEL", sessionKey(token));
  clearSessionCookie(res);
}

async function privateRecords() {
  const raw = await command("GET", `${NAMESPACE}:private-state`);
  const canonical = raw ? JSON.parse(raw) : { asks: [], suggestions: [], cleanup: [] };
  const pendingRows = await command("LRANGE", `${NAMESPACE}:queue:suggestion`, 0, -1);
  const pending = (pendingRows || []).map((row) => JSON.parse(row));
  const suggestions = [...(canonical.suggestions || [])];
  for (const row of pending) if (!suggestions.some((item) => item.id === row.id)) suggestions.push(row);
  const moderationRows = await command("LRANGE", `${NAMESPACE}:queue:moderation`, 0, -1);
  for (const rawRow of moderationRows || []) {
    const row = JSON.parse(rawRow);
    if (row.action !== "moderate_suggestion") continue;
    const suggestion = suggestions.find((item) => item.id === row.target_id);
    if (suggestion) suggestion.status = `${row.decision}_queued`;
  }
  return { asks: canonical.asks || [], suggestions };
}

async function cleanupReview() {
  const response = await fetch(CLEANUP_REVIEW, { cache: "no-store" });
  if (response.status === 404) return null;
  let data = {}; try { data = await response.json(); } catch (_) {}
  if (!response.ok || !data.bundle_id || !data.source_rulebook_hash || !data.replacement_hash) {
    throw Object.assign(new Error("cleanup review unavailable"), { status: 503, code: "cleanup_unavailable" });
  }
  return data;
}

function fail(res, error) { res.status(error.status || 500).json({ error: error.message, code: error.code || "internal_error" }); }

module.exports = { cleanText, requireJson, enqueue, existingEnqueue, reserveAction, command, session, requireSession, login, logout, setSessionCookie,
  clearSessionCookie, privateRecords, cleanupReview, fail, NAMESPACE };
