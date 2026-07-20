const C = require("./_collaboration.js");

module.exports = async (req, res) => {
  try {
    if (req.method !== "POST") { res.status(405).json({ error: "POST only", code: "method_not_allowed" }); return; }
    C.requireJson(req);
    const text = C.cleanText(req.body && req.body.text, 600);
    const key = C.cleanText(req.body && req.body.idempotency_key, 160);
    const result = await C.enqueue("SUGGESTION", { text, status: "pending_review" }, key);
    res.status(result.created ? 202 : 200).json({ ...result, status: "pending_review",
      message: result.created ? "Your suggestion was submitted for review." : "Your suggestion was already submitted for review." });
  } catch (error) { C.fail(res, error); }
};
