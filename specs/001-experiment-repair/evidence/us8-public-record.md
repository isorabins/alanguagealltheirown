# US8 Offline Evidence — Public Record and X

Result: **PASS for source/simulation; deployed desktop/mobile and approved X actions remain blocked**.

- Current negotiation, latest exam, collaboration, Conversation, and X status are open; rulebook, rejected history, prompts, exam rows, and full transcript use collapsed disclosure.
- A 760px responsive breakpoint covers the required 375px layout; the private page has its own 480px single-column boundary.
- X copy is at most 250 characters, X-only, and supplies both required `title` and `x_title` without thread fields.
- A stable id is persisted before side effects and sent as both request/idempotency identity. Synchronous success requires `results.x.success` plus a URL/id. Background work is polled by `request_id`; ambiguous timeouts poll before any retry.
- Dry/unconfirmed outcomes do not advance status/note watermarks or successful-post budget. Three failed upload attempts block one item; later notes continue; blocked count is public.
- Correction, explainer, and two verified follow candidates are prepared only. No post, pin, correction, or follow occurred.
- README and MECHANICS describe the implemented boundary and explicitly distinguish offline verification from production acceptance.
