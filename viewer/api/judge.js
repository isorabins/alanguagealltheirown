// POST {text, decoded} -> the audit: {key[], survived, total, corrupted[], missing[],
// invented[], fidelity, lost, mode}
// Two model calls: extract the answer key from the ORIGINAL (what must this message
// carry?), then grade the DECODED against it with the loop's real grader prompt.
// Fidelity arithmetic is ported from loop.py exactly.
const L = require("./_lib.js");

const KEY_SYS = "You extract the answer key from a message: a numbered list of every piece of " +
  "information it must carry to count as faithfully relayed — each quantity with its unit and " +
  "what it refers to, each identifier and name, each instruction with its condition and scope, " +
  "each time or deadline, each required ordering of steps. 4-20 items, one per line, each a " +
  "short self-contained statement. The key describes only what the message actually says. " +
  "Output ONLY the numbered list, nothing else.";

module.exports = async (req, res) => {
  try {
    const text = L.guard(req, res, "text", L.TEXT_MAX);
    if (text == null) return;
    const decoded = req.body && typeof req.body.decoded === "string" ? req.body.decoded.trim() : "";
    if (!decoded || decoded.length > 8000) { res.status(400).json({ error: "missing or oversized decoded" }); return; }

    const keyRaw = await L.call(L.MODEL_GRADER, KEY_SYS, text, { maxTokens: 700, temperature: 0 });
    const key = keyRaw.text.split("\n").map((l) => l.trim())
      .filter((l) => /^\d+[.):]?\s/.test(l))
      .map((l) => l.replace(/^\d+[.):]?\s*/, ""));
    if (key.length < 2) { res.status(502).json({ error: "could not extract an answer key from that text" }); return; }

    const keyTxt = key.map((k, i) => (i + 1) + ". " + k).join("\n");
    const gradeUser = "ORIGINAL:\n" + text + "\n\nANSWER KEY:\n" + keyTxt + "\n\nDECODED:\n" + decoded;
    const graded = await L.call(L.MODEL_GRADER, await L.getGraderPrompt(), gradeUser, { maxTokens: 1200, temperature: 0 });
    const m = graded.text.match(/\{[\s\S]*\}/);
    let g = {};
    try { g = m ? JSON.parse(m[0]) : {}; } catch (e) { g = {}; }

    const items = Array.isArray(g.items) ? g.items : [];
    const invented = Array.isArray(g.invented) ? g.invented : [];
    const ids = items.map((item) => Number(item && item.n));
    const complete = items.length === key.length && ids.every((n) => Number.isInteger(n) && n >= 1 && n <= key.length) &&
      new Set(ids).size === key.length && key.every((_, index) => ids.includes(index + 1)) &&
      items.every((item) => ["SURVIVED", "CORRUPTED", "MISSING"].includes(item && item.verdict));
    if (!complete) { res.status(502).json({ error: "judge returned invalid item coverage", code: "invalid_judgment" }); return; }
    const survived = items.filter((i) => i && i.verdict === "SURVIVED").length;
    let fidelity = items.length ? Math.round((100 * survived) / (key.length + invented.length)) : -1;
    if (g.mode === "RESPONDED" && fidelity >= 0) fidelity = Math.min(fidelity, 15);
    fidelity = fidelity >= 0 ? Math.max(0, Math.min(100, fidelity)) : -1;

    res.status(200).json({
      key: key.map((k, i) => (i + 1) + ". " + k),   // numbered, same shape as exam events
      survived,
      total: key.length,
      corrupted: items.filter((i) => i && i.verdict === "CORRUPTED").map((i) => i.n + ": " + (i.note || "")),
      missing: items.filter((i) => i && i.verdict === "MISSING").map((i) => i.n + ": " + (i.note || "")),
      invented,
      fidelity,
      lost: String(g.lost || (items.length ? "" : "grader output unparseable")).slice(0, 300),
      mode: g.mode === "RESPONDED" ? "RESPONDED" : "RELAY",
    });
  } catch (e) {
    L.sendError(res, e, "judge failed");
  }
};
