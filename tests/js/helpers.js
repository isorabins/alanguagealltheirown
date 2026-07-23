function response() {
  return { statusCode: 200, headers: {}, body: null,
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
    end() { this.body = null; return this; },
    setHeader(key, value) { this.headers[key.toLowerCase()] = value; } };
}
module.exports = { response };
