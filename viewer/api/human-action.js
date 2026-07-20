const C = require("./_collaboration.js");

module.exports = async (req, res) => {
  try {
    if (req.method !== "POST") { res.status(405).json({ error: "POST only", code: "method_not_allowed" }); return; }
    await C.requireSession(req);
    const body = req.body || {}; const action = body.action;
    if (!["answer_ask", "approve_suggestion", "dismiss_suggestion"].includes(action)) {
      res.status(400).json({ error: "invalid action", code: "invalid_action" }); return;
    }
    const target = C.cleanText(body.id, 160);
    const command = { id: target, action, created_at: Date.now() };
    if (action === "answer_ask") command.answer = C.cleanText(body.answer, 1200);
    const key = C.cleanText(body.idempotency_key, 160);
    const result = await C.enqueue("MODERATION", command, key);
    res.status(result.created ? 202 : 200).json({ ...result, status: result.created ? "queued" : "duplicate" });
  } catch (error) { C.fail(res, error); }
};
