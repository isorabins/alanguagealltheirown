// POST {encoded} -> {decoded}
// THE INVARIANT LIVES HERE: the stranger receives ONLY the rulebook and the encoded
// message. The original text never touches this endpoint.
const L = require("./_lib.js");

module.exports = async (req, res) => {
  try {
    const encoded = L.guard(req, res, "encoded", 6000);
    if (encoded == null) return;
    const expectedVersion = req.body && req.body.rulebook_version;
    const expectedHash = req.body && req.body.rulebook_hash;
    if (!expectedVersion || !expectedHash) { res.status(400).json({ error: "missing rulebook version", code: "invalid_input" }); return; }
    const rb = await L.getRulebook(true);
    const language = L.languagePayload(rb);
    if (expectedVersion !== language.version || expectedHash !== language.hash) {
      res.status(409).json({ error: "the language changed; encode again", code: "rulebook_changed",
        current_version: language.version, current_hash: language.hash }); return;
    }
    const decSys = "You are a fresh agent. You have never seen any prior conversation. Below is the " +
      "complete rulebook of a constructed language. Decode the message you receive: " +
      "reconstruct the original content as faithfully as you can. Do not invent anything " +
      "the message does not encode. Output ONLY the reconstruction.\n\n" + L.renderRulebook(rb);
    const dec = await L.call(L.MODEL_DECODER, decSys, encoded, { maxTokens: 1500, temperature: 0.1 });
    const decoded = dec.text.trim();
    if (!decoded) { res.status(502).json({ error: "decoder returned nothing" }); return; }
    res.status(200).json({ decoded, rulebook_version: language.version, rulebook_hash: language.hash });
  } catch (e) {
    L.sendError(res, e, "decode failed");
  }
};
