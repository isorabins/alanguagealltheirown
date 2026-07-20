const C = require("./_collaboration.js");

module.exports = async (req, res) => {
  try {
    if (req.method !== "POST") { res.status(405).json({ error: "POST only", code: "method_not_allowed" }); return; }
    const text = C.cleanText(req.body && req.body.text, 600);
    const key = C.cleanText(req.body && req.body.idempotency_key, 160);
    const result = await C.enqueue("SUGGESTION", { text, status: "pending_review" }, key);
    res.status(result.created ? 202 : 200).json({ ...result, status: result.created ? "pending_review" : "duplicate" });
  } catch (error) { C.fail(res, error); }
};
