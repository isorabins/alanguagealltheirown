#!/usr/bin/env node
// Local dev server for the try-it-yourself exam. Serves the REAL page (viewer/index.html)
// and mounts the production handlers (viewer/api/) at their production paths, so what you
// test locally is exactly what ships.
//   node tryit/serve.js    ->  http://localhost:8472
const http = require("http");
const fs = require("fs");
const path = require("path");

const VIEWER = path.join(__dirname, "..", "viewer");
const handlers = {
  "/api/encode": require(path.join(VIEWER, "api", "encode.js")),
  "/api/decode": require(path.join(VIEWER, "api", "decode.js")),
  "/api/judge": require(path.join(VIEWER, "api", "judge.js")),
};

function shim(res) {
  res.status = (code) => { res.statusCode = code; return res; };
  res.json = (obj) => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(obj)); };
  return res;
}

http.createServer((req, res) => {
  shim(res);
  const url = (req.url || "").split("?")[0];
  if (req.method === "GET" && (url === "/" || url === "/index.html")) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end(fs.readFileSync(path.join(VIEWER, "index.html")));
    return;
  }
  if (req.method === "GET" && url === "/state.js") {
    res.setHeader("Content-Type", "text/javascript");
    res.end(fs.readFileSync(path.join(VIEWER, "state.js")));
    return;
  }
  const h = handlers[url];
  if (!h) { res.status(404).json({ error: "not found" }); return; }
  let body = "";
  req.on("data", (c) => { body += c; if (body.length > 32768) req.destroy(); });
  req.on("end", () => {
    try { req.body = body ? JSON.parse(body) : {}; } catch (e) { req.body = {}; }
    Promise.resolve(h(req, res)).catch((e) => {
      if (!res.writableEnded) res.status(500).json({ error: String(e.message || e) });
    });
  });
}).listen(8472, () => console.log("try-it dev server (real page): http://localhost:8472"));
