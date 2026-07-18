#!/usr/bin/env node
// Local dev server for the try-it-yourself exam. Mounts the Vercel-style handlers
// in tryit/api/ at the same paths they will have in production (/api/encode etc.),
// so the demo page works unchanged when the feature ships.
//   node tryit/serve.js    ->  http://localhost:8472
const http = require("http");
const fs = require("fs");
const path = require("path");

const handlers = {
  "/api/encode": require("./api/encode.js"),
  "/api/decode": require("./api/decode.js"),
  "/api/judge": require("./api/judge.js"),
};

function shim(res) {
  res.status = (code) => { res.statusCode = code; return res; };
  res.json = (obj) => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(obj)); };
  return res;
}

http.createServer((req, res) => {
  shim(res);
  if (req.method === "GET" && (req.url === "/" || req.url === "/index.html")) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end(fs.readFileSync(path.join(__dirname, "index.html")));
    return;
  }
  const h = handlers[(req.url || "").split("?")[0]];
  if (!h) { res.status(404).json({ error: "not found" }); return; }
  let body = "";
  req.on("data", (c) => { body += c; if (body.length > 32768) req.destroy(); });
  req.on("end", () => {
    try { req.body = body ? JSON.parse(body) : {}; } catch (e) { req.body = {}; }
    Promise.resolve(h(req, res)).catch((e) => {
      if (!res.writableEnded) res.status(500).json({ error: String(e.message || e) });
    });
  });
}).listen(8472, () => console.log("try-it dev server: http://localhost:8472"));
