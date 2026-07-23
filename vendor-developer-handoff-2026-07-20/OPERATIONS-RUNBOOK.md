# Operations and Safety Runbook

## Planning Start

1. Read the handoff and nearest workspace/project instructions.
2. Re-run read-only git checks, including `git ls-remote origin refs/heads/main`; the local tracking ref may be stale.
3. Create a clean worktree and feature branch from the current remote commit, planned as `codex/experiment-repair`.
4. Continue project-local Spec Kit: clarify if necessary, plan, tasks, analyze.
5. Stop for Iso's approval before implementation.

## Safe Local Verification

- Use temporary directories or copied fixture state.
- Unit-test renderers, parser authority, judge validation, queue transitions, idempotency, and UI states without real provider calls where possible.
- Stub OpenRouter, Upload-Post, authentication, spending-cap, and timeout responses.
- Run the static viewer against fixture snapshots.
- Preserve every current state artifact; never normalize production state during a test.

## Commands That Are Not Harmless

- `python3 loop.py` and `run_turn.sh` can advance the experiment and spend money.
- `tweet.py` can publish externally.
- `vercel deploy --prod` changes the public site.
- Vercel/OpenRouter environment and key operations change credentials or billing boundaries.
- Replacing production `state/*.json` changes the public record.

Do not run these until the corresponding approved planned stop.

## Live Planned Stops

Separate approval is required before:

1. Pausing or resuming the production loop.
2. Applying the cleanup result to canonical rule state.
3. Creating/changing production API keys, limits, secrets, or sessions.
4. Deploying the website or changing production behavior.
5. Publishing the correction or explainer, pinning a post, or following accounts.
6. Pushing or merging to `main`.

## Deployment Facts to Reverify

- Historical runtime: VPS timer executes the loop approximately every 15 minutes.
- Historical site path: explicit Vercel deployment from `viewer/`; the project is not git-linked.
- Historical state publication: loop writes `viewer/state.js`; later remote commits may contain generated state only.
- Historical provider routing: OpenRouter for model calls; Upload-Post for X.

Treat every item above as a hypothesis until the implementation chat re-verifies it from the current environment. Never expose credential contents in logs or chat.

## Failure Behavior

- Missing approval: stop before mutation.
- Missing secret or cap metadata: mark production acceptance blocked, not complete.
- Cleanup mismatch: preserve snapshot and diff; do not apply.
- Invalid judge coverage: mark exam invalid; publish no score.
- Research/ASK/suggestion queue error: do not inject partial or uncorrelated text.
- X ambiguous/failure response: retain the same idempotency identity; do not mark posted; block after three attempts and continue.
- Public monthly allowance exhausted: show the allowance message and do not relabel unrelated errors.

