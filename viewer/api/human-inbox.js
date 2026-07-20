const C = require("./_collaboration.js");

module.exports = async (req, res) => {
  try {
    if (req.method !== "GET") { res.status(405).json({ error: "GET only", code: "method_not_allowed" }); return; }
    const current = await C.requireSession(req);
    const records = await C.privateRecords();
    const cleanup = await C.cleanupReview();
    res.status(200).json({ expires_at: current.expires_at, ...records, cleanup });
  } catch (error) { C.fail(res, error); }
};
