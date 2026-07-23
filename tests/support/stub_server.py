"""Deterministic local HTTP stub for provider-shaped tests; never calls the network."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StubHandler(BaseHTTPRequestHandler):
    routes = {}
    requests = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length", "0")))
        self.__class__.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
        status, payload = self.__class__.routes.get(self.path, (404, {"error": "not stubbed"}))
        encoded = json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)

    def log_message(self, *_):
        pass


def server(routes):
    StubHandler.routes = routes; StubHandler.requests = []
    instance = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
    return instance
