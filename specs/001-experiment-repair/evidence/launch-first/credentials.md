# Launch-First Production Credentials

Date: 2026-07-24 WITA

Status: **PASS**

No secret value is recorded in this evidence.

## Public inference

- Created a distinct OpenRouter key named `alato-public-production`.
- Non-secret key hash:
  `2e1f395b5f81af901beb3b784a05061ff4b6c255b8794dffe0920938aa88d867`.
- Limit: `$20`.
- Reset: monthly.
- Starting usage: `$0`; starting remaining allowance: `$20`.
- Enabled: yes; expiry: none.
- Stored in Bitwarden as `ALATO_OPENROUTER_PUBLIC_PRODUCTION_API_KEY`.
- Installed in Vercel Production as sensitive
  `OPENROUTER_PUBLIC_API_KEY`.
- The experiment worker continues to use the pre-existing private
  `OPENROUTER_API_KEY`; the public key is therefore separately named and
  separately capped.

## Collaboration and human review

- Reused the empty, already-tested Upstash database
  `alato-preview-acceptance` (`store_7q99nswrwsCpDvJF`).
- Verified the REST endpoint returned HTTP 200 and the database was empty at
  Production setup.
- Installed sensitive Vercel Production variables
  `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, and `HUMAN_PASSWORD`.
- Installed the matching Redis URL/token names on the VPS for the bounded
  collaboration courier.
- Verified the deployed human-session lifecycle:
  login 204, authenticated read 200, logout 204, post-logout read 401.

## Readback

`vercel env ls production --cwd viewer` listed exactly the new sensitive
Production names above plus the existing private `OPENROUTER_API_KEY`; values
were encrypted and not printed.
