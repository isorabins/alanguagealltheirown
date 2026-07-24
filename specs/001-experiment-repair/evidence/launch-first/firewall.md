# Launch-First Login Firewall

Date: 2026-07-24 WITA

Status: **PASS**

- Vercel firewall configuration version: `1`.
- Active rule id: `rule_protect_human_login_sufq63`.
- Rule name: `Protect human login`.
- Match: `POST /api/human-session`.
- Scope: requesting IP.
- Action: fixed-window rate limit.
- Boundary: 10 requests per 600 seconds.

The current Hobby plan supports one rate-limit rule, so the single available
rule protects the credential-bearing login endpoint.
