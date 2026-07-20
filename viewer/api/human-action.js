const C = require("./_collaboration.js");

module.exports = async (req, res) => {
  try {
    if (req.method !== "POST") { res.status(405).json({ error: "POST only", code: "method_not_allowed" }); return; }
    C.requireJson(req);
    await C.requireSession(req);
    const body = req.body || {}; const action = body.action;
    if (!["answer_ask", "moderate_suggestion"].includes(action)) {
      res.status(400).json({ error: "invalid action", code: "invalid_action" }); return;
    }
    const target = C.cleanText(body.id, 160);
    const command = { target_id: target, action, created_at: Date.now() };
    if (action === "answer_ask") {
      command.answer = C.cleanText(body.answer, 1200);
    } else {
      if (!["approved", "dismissed"].includes(body.decision)) {
        res.status(400).json({ error: "invalid decision", code: "invalid_action" }); return;
      }
      command.decision = body.decision;
    }
    const key = C.cleanText(body.idempotency_key, 160);
    const reservation = { action, id: target, answer: command.answer, decision: command.decision };
    if (!await C.reserveAction(target, reservation)) {
      res.status(409).json({ error: "contradictory action already queued", code: "action_conflict" }); return;
    }
    const existing = await C.existingEnqueue("MODERATION", key);
    if (existing) { res.status(200).json({ ...existing, status: "duplicate" }); return; }
    const records = await C.privateRecords();
    if (action === "answer_ask") {
      const ask = records.asks.find((row) => row.id === target);
      if (!ask || ask.status !== "awaiting_iso") { res.status(409).json({ error: "question is not open", code: "closed_id" }); return; }
    } else {
      const suggestion = records.suggestions.find((row) => row.id === target);
      if (!suggestion || suggestion.status !== "pending_review") {
        res.status(409).json({ error: "suggestion is not open", code: "closed_id" }); return;
      }
    }
    const result = await C.enqueue("MODERATION", command, key);
    res.status(result.created ? 202 : 200).json({ ...result, status: result.created ? "queued" : "duplicate" });
  } catch (error) { C.fail(res, error); }
};
