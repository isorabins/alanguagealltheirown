# Structured Legislative Protocol — Live Acceptance

Date: 2026-07-29 WITA
Approval: `APPROVE LIVE CHANGE: alato-structured-protocol-cost-and-receipts-20260729-turn1165-g16`
Result: **PASS**

## Release and rollback boundary

- PR [#11](https://github.com/isorabins/alanguagealltheirown/pull/11)
  merged as `e8fffe691e8359242b9bcc8a27c23200f823191a`.
- Before activation, the paused turn-1165 VPS state was archived at
  `/root/alato-rollbacks/20260729-turn1165-structured-g16/state.tar.gz`;
  SHA-256:
  `18e4f55f31559dc58d2f18d01599ab0e0e21cfa11ef6b6f00f2d07484831867c`.
- The VPS fast-forwarded cleanly, passed 115 Python tests, 31 JavaScript
  tests, and contract coverage for 102 requirements / 194 tasks before the
  timer resumed.
- The initial application estimate was `$4.137152`; the authenticated private
  OpenRouter key baseline was `$7.184518119`.

## Canary defect and bounded repairs

Natural turn 1166 exposed a semantic schema defect: B could satisfy the
provider schema with punctuation-only deliberation and a null motion while
`rule-129` was open. The resulting authoritative receipt was internally
consistent but left the proposal open. The timer was paused at clean commit
`4b6c7af92740ff4fadc7bad041817bd010e4c0f3`.

PR [#12](https://github.com/isorabins/alanguagealltheirown/pull/12) merged as
`2504699b8b88887e01c1b585be524a9e145bb6e8`. It requires substantive
deliberation on every new action and a non-null ADOPT, REJECT, or REQUEST from
B whenever a motion is open. The production host then passed 116 Python tests,
31 JavaScript tests, and full contract coverage.

The next scheduled turn failed before a provider call because that same stricter
input type tried to re-validate the immutable turn-1166 receipt. The timer
paused automatically at turn 1167 with the exact error:

```text
PostStateReceipt.attempted_action.deliberation
String should have at least 12 characters
```

PR [#13](https://github.com/isorabins/alanguagealltheirown/pull/13) merged as
`aba8e9f39554ed42e7b9608a0989c6282d9c4e61`. It separates current model-input
policy from the stable receipt record shape. The actual turn-1166 receipt then
constructed turn 1168 successfully off-live, while the current B/open schema
continued to reject punctuation and null motions. The production host passed
117 Python tests, 31 JavaScript tests, and full contract coverage before the
timer returned to its normal boundary.

## Natural live sequence

| Turn | Result | Authoritative state evidence |
|---|---|---|
| 1167 | Ordinary exam, valid, 92% fidelity, -28% tokens | `tests_run=383`; no rulebook change |
| 1168 | A revised open `rule-129` on the first structured attempt | changed ids exactly `["rule-129"]`; 22 adopted; adopted-language hash unchanged |
| 1169 | B rejected `rule-129` on the first structured attempt | changed ids exactly `["rule-129"]`; open motion `null`; 22 adopted; adopted-language hash unchanged |
| 1170 | Ordinary exam plus scheduled Conversation | exam valid at 100% fidelity and -40% tokens; `tests_run=384` |

`conversation-1170` is the first Conversation artifact after historical turn
1074. It contains six non-empty A/B messages. Its judge returned ids 1–4
exactly once with boolean `pass=true`, no contradictions, and
`judgment.valid=true`. The artifact is pinned to adopted-language hash
`6d1b39ca6d9cb092c7a8c07098e499967a2eae26cdcd595dc7ad0cb056adb01c`
and artifact hash
`dcbc2acc4f7a209352c2f9f35d5887d0c20e23610aab27b1e8d8d0ef60bf50bf`.

Final rule statuses were 22 adopted, 1 repealed, 25 rejected, and 76
historical, with no open motion. Autonomous governance changed only
`rule-129`; the adopted language and its hash did not change.

## Cost, collaboration, and service evidence

- The gitignored local ledger contained 30 unique OpenRouter response ids and
  exact post-cutover cost `$0.08812660055`.
- The authenticated provider key read `$7.272644712`; delta from the baseline
  was `$0.088126593`, equal to the ledger within endpoint rounding and below
  the approved `$0.25` ceiling.
- All five human answers reached `delivered`; all 17 research/lookup records
  reached `delivered`; 22 delivery ids were unique. The prior live internal
  lookups retained project citations, `cost_usd=0`, and
  `web_search_requests=0`.
- `state/collaboration-sync.log` retained its historical 2026-07-24 mtime
  throughout the canary, so no new courier warning occurred.
- At turn 1170, the VPS was clean and equal to `origin/main`, the one-shot
  service was inactive after success, and `language-loop.timer` was active for
  the next normal boundary.

## Public read-only smoke

`https://alanguagealltheirown.com/` and `/human` both returned HTTP 200. The
public raw canonical files reported `tests_run=384` and
`conversation-1170` with six messages and a valid judgment.

No manual rule edit, credential/key-limit change, DNS change, Vercel deploy,
prompt/model/cadence change, X post, or unrelated production behavior was
performed.
