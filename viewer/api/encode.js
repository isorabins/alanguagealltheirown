// POST {text} -> {encoded, orig_tokens, enc_tokens, delta_pct, rulebook_version}
// Runs the real encoder: same model, same system prompt, same rulebook as the loop's exams.
const L = require("./_lib.js");
const crypto = require("crypto");

module.exports = async (req, res) => {
  try {
    if (!L.requireJson(req, res)) return;
    const text = L.guard(req, res, "text", L.TEXT_MAX);
    if (text == null) return;
    const rb = await L.getRulebook();
    const language = L.languagePayload(rb);
    const rbook = L.renderRulebook(rb);
    const encSys = "You are the encoder. Encode the message below into the project language " +
      "using ONLY this rulebook. Where the rulebook is silent, fall back to plain " +
      "English for that part. Output ONLY the encoded message, nothing else.\n\n" + rbook;
    const enc = await L.call(L.MODEL_ENCODER, encSys, text, { maxTokens: 1500, temperature: 0.3 });
    const encoded = enc.text.trim();
    if (!encoded) { res.status(502).json({ error: "encoder returned nothing" }); return; }
    const orig_tokens = await L.tokenCount(text);
    const enc_tokens = await L.tokenCount(encoded);
    res.status(200).json({
      journey_id: crypto.randomUUID(),
      encoded,
      orig_tokens,
      enc_tokens,
      delta_pct: Math.round(((enc_tokens - orig_tokens) / orig_tokens) * 100),
      rulebook_version: language.version,
      rulebook_hash: language.hash,
    });
  } catch (e) {
    L.sendError(res, e, "encode failed");
  }
};
