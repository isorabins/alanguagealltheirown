// POST {encoded} -> {decoded}
// THE INVARIANT LIVES HERE: the stranger receives ONLY the rulebook and the encoded
// message. The original text never touches this endpoint.
const L = require("./_lib.js");

module.exports = async (req, res) => {
  try {
    const encoded = L.guard(req, res, "encoded", 6000);
    if (encoded == null) return;
    const rb = await L.getRulebook();
    const decSys = "You are a fresh agent. You have never seen any prior conversation. Below is the " +
      "complete rulebook of a constructed language. Decode the message you receive: " +
      "reconstruct the original content as faithfully as you can. Do not invent anything " +
      "the message does not encode. Output ONLY the reconstruction.\n\n" + L.renderRulebook(rb);
    const dec = await L.call(L.MODEL_DECODER, decSys, encoded, { maxTokens: 1500, temperature: 0.1 });
    const decoded = dec.text.trim();
    if (!decoded) { res.status(502).json({ error: "decoder returned nothing" }); return; }
    res.status(200).json({ decoded });
  } catch (e) {
    res.status(500).json({ error: "decode failed: " + e.message });
  }
};
