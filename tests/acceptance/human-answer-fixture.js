const fs = require("fs");
const http = require("http");
const path = require("path");

const humanHtml = fs.readFileSync(path.join(__dirname, "../../viewer/human.html"), "utf8");
const expireFirstSubmit = process.argv.includes("--expire-first-submit");
let loggedIn = true;
let expiredOnce = false;
let expiresAt = Date.now() + 30 * 60 * 1000;
const ask = {
  id: "ask-fixture-1",
  requester: "B",
  question: "Which evidence route should internal project questions use?",
  status: "awaiting_iso",
};

function send(res, status, body, type = "application/json") {
  res.writeHead(status, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(type === "application/json" ? JSON.stringify(body) : body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => { raw += chunk; });
    req.on("end", () => {
      try { resolve(raw ? JSON.parse(raw) : {}); } catch (error) { reject(error); }
    });
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && (req.url === "/" || req.url === "/human")) {
      send(res, 200, humanHtml, "text/html; charset=utf-8");
      return;
    }
    if (req.method === "GET" && req.url === "/api/human-inbox") {
      if (!loggedIn) { send(res, 401, { error: "human session required", code: "unauthorized" }); return; }
      send(res, 200, { expires_at: expiresAt, asks: [ask], suggestions: [], cleanup: null });
      return;
    }
    if (req.method === "POST" && req.url === "/api/human-action") {
      if (expireFirstSubmit && !expiredOnce) {
        expiredOnce = true;
        loggedIn = false;
        send(res, 401, { error: "human session required", code: "unauthorized" });
        return;
      }
      if (!loggedIn) { send(res, 401, { error: "human session required", code: "unauthorized" }); return; }
      const body = await readBody(req);
      ask.status = "answer_pending";
      ask.answer = body.answer;
      ask.answer_submitted_at = Date.now();
      send(res, 202, { id: "moderation-fixture-1", created: true, status: "queued" });
      return;
    }
    if (req.method === "POST" && req.url === "/api/human-session") {
      await readBody(req);
      loggedIn = true;
      expiresAt = Date.now() + 30 * 60 * 1000;
      send(res, 200, { expires_at: expiresAt });
      return;
    }
    if (req.method === "DELETE" && req.url === "/api/human-session") {
      loggedIn = false;
      res.writeHead(204);
      res.end();
      return;
    }
    send(res, 404, { error: "not found" });
  } catch (error) {
    send(res, 500, { error: error.message });
  }
});

server.listen(0, "127.0.0.1", () => {
  const address = server.address();
  console.log(`http://127.0.0.1:${address.port}/human`);
});
