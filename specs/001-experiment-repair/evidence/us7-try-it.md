# US7 Offline Evidence — Try It

Result: **PASS for handler contracts; real key metadata/cap and deployed journey remain blocked by G5/G10**.

- Encode returns the adopted-language version/hash; decode refetches canonical state and returns `409 rulebook_changed` before a model call on mismatch.
- Every public provider call requires `OPENROUTER_PUBLIC_API_KEY`. `OPENROUTER_API_KEY` is not read or accepted as fallback.
- Verified monthly-limit exhaustion maps to `allowance_exhausted`; authentication, rate, network, empty response, and provider failures remain distinct.
- The browser preserves version/hash and shows separate re-encode, monthly reopening, and unrelated provider-failure messages.
- No paid call or production credential/configuration change was made.
