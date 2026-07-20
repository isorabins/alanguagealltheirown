const crypto = require("crypto");

const NAMESPACE = "alato:v1";
const SESSION_SECONDS = 30 * 60;

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
  const clean = value.replace(/\s+/g, " ").trim();
  if (!clean || clean.length > max) throw Object.assign(new Error("text must contain 1-" + max + " characters"),
    { status: 400, code: "invalid_input" });
  return clean;
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

function cookies(req) {
  return Object.fromEntries(String(req.headers.cookie || "").split(";").map((part) => part.trim().split(/=(.*)/s).slice(0, 2))
    .filter((pair) => pair.length === 2).map(([key, value]) => [key, decodeURIComponent(value)]));
}

async function session(req) {
  const token = cookies(req).alato_human;
  if (!token || !/^[a-f0-9]{64}$/.test(token)) return null;
  const raw = await command("GET", `${NAMESPACE}:session:${token}`);
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
  const supplied = Buffer.from(String(password || "")); const target = Buffer.from(expected);
  if (supplied.length !== target.length || !crypto.timingSafeEqual(supplied, target)) {
    throw Object.assign(new Error("wrong password"), { status: 401, code: "wrong_password" });
  }
  const token = crypto.randomBytes(32).toString("hex");
  const value = JSON.stringify({ created_at: Date.now(), expires_at: Date.now() + SESSION_SECONDS * 1000 });
  await command("SET", `${NAMESPACE}:session:${token}`, value, "EX", SESSION_SECONDS, "NX");
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
  if (token && /^[a-f0-9]{64}$/.test(token)) await command("DEL", `${NAMESPACE}:session:${token}`);
  clearSessionCookie(res);
}

async function privateRecords() {
  const raw = await command("GET", `${NAMESPACE}:private-state`);
  const canonical = raw ? JSON.parse(raw) : { asks: [], suggestions: [], cleanup: [] };
  const pendingRows = await command("LRANGE", `${NAMESPACE}:queue:suggestion`, 0, -1);
  const pending = (pendingRows || []).map((row) => JSON.parse(row));
  const suggestions = [...(canonical.suggestions || [])];
  for (const row of pending) if (!suggestions.some((item) => item.id === row.id)) suggestions.push(row);
  return { ask: canonical.asks || [], suggestion: suggestions, cleanup: canonical.cleanup || [] };
}

function fail(res, error) { res.status(error.status || 500).json({ error: error.message, code: error.code || "internal_error" }); }

module.exports = { cleanText, enqueue, command, session, requireSession, login, logout, setSessionCookie,
  clearSessionCookie, privateRecords, fail, NAMESPACE };
