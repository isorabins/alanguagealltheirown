# Validation Quickstart: Experiment Repair

This is the run guide, not implementation approval. Commands that can call paid
providers, touch production state, deploy, publish, change credentials/caps, or
push/merge `main` remain blocked until their named live gate is approved.

## 1. Establish the exact source and evidence folder

Record:

- feature branch and commit;
- current `origin/main` and divergence;
- production VPS commit/turn/rulebook version;
- Vercel deployment id, production URL, and environment names only;
- approved gate receipts;
- test-data ids and cleanup path.

Create `specs/001-experiment-repair/evidence/<run-id>/` with:

```text
matrix.md
receipts/
screenshots/
00-cross-turn-workflow.mp4
cleanup.md
```

Never capture password, cookie, OTP, API key, Redis token, or provider secret.

## 2. Offline contract suite

Run against copied fixtures only:

```bash
python3 -m unittest discover -s tests/python -p 'test_*.py'
node --test tests/js/*.test.js
python3 tests/acceptance/check_contract_coverage.py
! rg -n "RedisRest|sync_remote" loop.py
rg -n "collab_sync.py (pull|push)|timeout" run_turn.sh
```

Required results:

- every ordinary encoder/decoder/Conversation/Try It prompt contains every
  adopted rule and zero proposed/rejected/reverted/outside text;
- only an explicit proposal trial adds one labeled proposal;
- forbidden A/B motions, repeats, malformed ids, no-ops, and overflow mutate
  nothing;
- judge scores only exact one-to-one answer-key coverage;
- inbox enqueue/claim/ack and restart fixtures deliver each id once;
- courier exceptions/replays cannot write canonical collaboration outside the loop or cancel a turn;
- legacy proposed/reverted rules are terminalized by cleanup before one-open enforcement;
- repeal motions never enter the adopted language view and preserve full history;
- pending/dismissed suggestions reach neither public snapshots nor prompts;
- Try It normal, version mismatch, cap, and provider failure are distinct;
- X dry/failure/timeout/async/partial/retry fixtures cannot falsely post or
  create attempt 4;
- active dumb-script references are absent while historical artifacts remain.

If any invariant test fails, stop. A UI pass cannot compensate.

## 3. Cleanup dry run on an immutable copy

After the paid scratch-call gate, run the cleanup tool only with an explicit
copied state directory and output directory. Confirm the source hash before and
after. Before a paid request, generate the source-specific strict response schema
and verify that its required assignment keys exactly equal the adopted source-id
set. Route only to a provider endpoint that accepts the schema parameter. Compile
the returned assignments/groups locally; missing/extra assignments or
unknown/orphan/duplicate groups must stop before B. The output must contain
schema/request metadata, original, compiled A replacement, B audit, exact diff,
and manifest; production must remain byte-identical.

Stop for Iso's separate exact approval before any apply command.

## 4. Production-equivalence preflight

Before merge/deploy, verify by read-only checks:

- reviewed commit is the commit proposed for `main` and deploy;
- VPS timer state is known and matches the pause/resume gate;
- deployed functions are Node 24 and the public URL targets the intended Vercel
  deployment;
- required environment names exist without printing values;
- Upstash is reachable from a non-production fixture namespace;
- public OpenRouter key metadata shows `$20`, monthly reset, and a different
  identity/hash from the private experiment key;
- Upload-Post profile and X target are known, but no post/follow/pin occurs;
- rollback commits, prior Vercel deployment id, original rulebook snapshot, and
  test-data cleanup actions are recorded.

Missing access, identity, approval, or secret is `BLOCKED`, not a partial pass.

## 5. Create the evidence matrix before visible testing

Use one row per feature and failure state. Each row names:

| Field | Required content |
|---|---|
| Visible action | Natural human action through the deployed site/X profile |
| Expected result | Exact visible state |
| Screenshot | Numbered filename with location, target, and state |
| Continuous video | Timestamp range when cross-turn continuity matters |
| Receipt | Independent read-only state/log/provider/profile proof |
| Cleanup | Visible or approved removal/reversal action |
| Result | `PASS`, `FAIL`, or `BLOCKED` only |

The matrix must include all twelve production checks in `spec.md`, plus wrong
password, expired session, duplicate submission, rapid requests, script/HTML,
prompt injection, provider timeout, no research evidence, rulebook change during
Try It, cap exhaustion, and three X failures.

## 6. Human-app-testing production run

Before the live gate, run the reusable Crabbox skill against a fresh
off-production fixture. Require a verified v0.40.0 binary, exact provider and
coordinator identity, one CPX32 Germany lease, eight-hour TTL, projected total
within the `$2` ceiling, protected env-profile allowlist, named evidence paths,
and coordinator-owned cleanup. Fail closed on any mismatch.

Use the exclusive remote X11 desktop for the real deployed site, real `/human`,
and real X profile only within approved gates; Iso's visible Mac is not the
recording surface. Start the outer desktop video before the first visible action,
visibly close and relaunch the browser while recording continues, and pause or
obscure recording for password and secret entry.

Minimum screenshot sequence:

1. deployed commit/version and public landing state;
2. adopted-only language boundary and current history labels;
3. A allowed/forbidden role behavior and no-op receipt;
4. B allowed/forbidden role behavior and no-op receipt;
5. cleanup original/A/B/diff and visible pre-apply stop;
6. RESEARCH open, persisted after reload/restart, result/no-evidence, delivered;
7. ASK awaiting Iso;
8. `/human` wrong password;
9. `/human` login, private inbox, refresh, browser restart, expiry, and logout;
10. ASK answered and exact question+answer delivered once after restart;
11. suggestion directly below agents, pending-private, approve/dismiss, persisted,
    approved public record, delivered once as optional context;
12. full six-message Conversation plus concrete judgment;
13. Try It normal, version mismatch, cap exhaustion, provider error;
14. selective collapse and complete journeys on desktop;
15. the same required journeys at 375px width;
16. README/MECHANICS/page copy matching observed behavior;
17. approved correction, confirmed single-post result, retry/block receipt,
    explainer, pin, and individually approved follows on the real X profile;
18. visible cleanup and final empty/stable queues with no warnings.

Backend/log/API checks are supporting receipts only after the visible action.
They cannot replace the screenshot/video row.

After the run, verify the MP4 is continuous and playable, every numbered image
maps to the matrix, secret scanning/manual evidence review passes, actual spend
is at or below `$2`, the coordinator reports no active lease, and the provider
independently reports no remaining pilot server.

## 7. Bounded repair loop

Run at most three complete test/fix/retest loops. Stop earlier if the same blocker
survives two loops or a required visible surface, access, production identity, or
approval is missing. Re-run failed steps and one full smoke journey after each
repair.

## 8. Historical integrity and cleanup

After visible testing, verify:

- rejected/proposed history remains readable;
- pre-cleanup snapshot hashes are unchanged;
- baseline state diff shows only the documented empty public-collaboration scaffold;
- last-ten passing-exam average was not reset or forked;
- no invalid exam has a published fidelity score;
- no dry/failed X action is marked posted;
- no pending/dismissed suggestion is public;
- no duplicate collaboration delivery or post exists;
- no stuck lease/queue item, disposable test item, dirty production file, or
  silent timer/site warning remains.

Remove disposable data through the approved visible product path. Do not edit
Redis, GitHub JSON, or production files directly as a testing shortcut.

## 9. Closeout

Run convergence before claiming completion. If only offline, preview, dry-run,
or partially approved production work passed, update the spec implementation
ledger and tasks with the current pass, official planned stop, and remaining
gaps. Final result is `PASS`, `FAIL`, or `BLOCKED`; `PASS` requires every matrix
row, complete evidence, cleanup, clean git state, scoped commits, and verified
live surfaces.
