# Current Official Documentation Receipt

Verified on 2026-07-20 without credentials or paid calls:

- OpenRouter's current web-search server tool is `tools: [{"type":"openrouter:web_search"}]`; the plugin and `:online` form are deprecated. The tool is beta and returns standardized URL citation annotations. Source: <https://openrouter.ai/docs/guides/features/server-tools/web-search>
- OpenRouter key creation supports a USD `limit` and `limit_reset: "monthly"`; monthly resets occur at midnight UTC. Source: <https://openrouter.ai/docs/api/api-reference/api-keys/create-keys>
- OpenRouter's public model catalog contains `deepseek/deepseek-v3.2` and `moonshotai/kimi-k2.6` on this date.
- Upstash Redis REST accepts Redis commands as JSON arrays and provides `/multi-exec`; ordinary pipelines are explicitly non-atomic. Source: <https://upstash.com/docs/redis/features/restapi>
- Upload-Post's text endpoint remains `/api/upload_text`; implementation must confirm the X-specific result instead of treating any HTTP response as delivery. Source: <https://docs.upload-post.com/api/upload-text/>
- Vercel WAF route rate limiting remains available and is the planned production perimeter control. Source: <https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting>

No material contract drift was found. Because the OpenRouter search tool is beta and Upload-Post receipt shapes can vary, both parsers remain defensive and their production-equivalent validation stays behind G10/G11.
