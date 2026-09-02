const TEXT_MAX = 700;
const PER_IP_PER_HOUR = 6;
const GLOBAL_PER_DAY = 150;

class ProviderError extends Error {
  constructor(code, message, status) { super(message); this.code = code; this.status = status || 502; }
}

// Public model work is intentionally absent. The disabled Try It handlers do
// not retain an alternate provider, budget, or adopted-language authority.

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

module.exports = { guard, requireJson, sendError, ProviderError, TEXT_MAX };
