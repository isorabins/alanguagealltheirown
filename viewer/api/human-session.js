const C = require("./_collaboration.js");

module.exports = async (req, res) => {
  try {
    if (req.method === "GET") {
      const current = await C.session(req);
      if (!current) { res.status(401).json({ authenticated: false, code: "unauthorized" }); return; }
      res.status(200).json({ authenticated: true, expires_at: current.expires_at }); return;
    }
    if (req.method === "POST") {
      C.requireJson(req);
      const result = await C.login(req.body && req.body.password);
      C.setSessionCookie(res, result.token);
      res.status(204).end(); return;
    }
    if (req.method === "DELETE") {
      await C.logout(req, res); res.status(204).end(); return;
    }
    res.status(405).json({ error: "unsupported method", code: "method_not_allowed" });
  } catch (error) { C.fail(res, error); }
};
