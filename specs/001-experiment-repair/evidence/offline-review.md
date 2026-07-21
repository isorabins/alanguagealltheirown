# Offline Diff and Safety Review

Reviewed on 2026-07-21 against implementation baseline `96e681f`. A read-only fetch
observed moving remote `main` at `73a71cf`; those 88 later commits changed only generated
state/viewer snapshots and are intentionally left for the approved paused rebase at T113.

| Check | Evidence | Result |
|---|---|---|
| Scope | Changed paths are limited to the approved Spec Kit/handoff, experiment runtime, prompts, viewer, tests, and evidence surfaces. | PASS |
| Secrets | Pattern scan found no credential values. Tests contain only explicit fake values. | PASS |
| Baseline-aware state | The five pre-existing production-derived files match their `96e681f` hashes. Only empty sanitized `state/public-collaboration.json` is added. The moving remote snapshots were not copied backward into the feature worktree. | PASS |
| Paid/network effects | Tests used mocks and one `127.0.0.1` stub. No paid provider or production API call ran. | PASS |
| Loop sole-writer boundary | `loop.py` contains neither `RedisRest` nor `sync_remote`. It alone imports the atomic local inbox spool and writes canonical collaboration history. | PASS |
| Courier failure boundary | `collab_sync.py` has bounded two-second REST calls, `run_turn.sh` adds an eight-second wall-clock bound plus `|| true`, and tests cover exception, durable-spool-before-ack, replay, recovery, and outbox publication. | PASS |
| Rule authority | One add or repeal motion can be open. A alone originates/revises; B alone audits/adopts/rejects. Wrong-role, stale, repeated, malformed, settled, and terminal motions are reason-coded no-ops. | PASS |
| Repeal isolation | Pending repeal stays attached to an adopted target but outside all language views; adoption terminalizes the target as `repealed`, retains history, and permits the same wording only as a fresh future proposal. | PASS |
| Cleanup integrity | Candidate and audit bind exact hashes; adopted/proposed/reverted legacy entries become historical with receipts; pending repeal state is cleared; application still requires the exact approval receipt. | PASS |
| Judge/metadata integrity | Invalid ordinary exams show `no valid score`, exact matched motion lines drive rationale, corpus exam metadata is capped at 500, and the dead economics stub is absent. | PASS |
| Collaboration privacy | Stable ids, atomic transport receipts, loop-owned reconciliation, processed-id dedupe, requester-only delivery, and sanitized-only public fetching are tested. | PASS |
| X truthfulness | Existing sync/async/partial/non-2xx/network/timeout/pending/three-attempt/later-note cases cannot falsely advance posted state. | PASS |
| User-work overlap | Source checkout still has only its prior modified `PROGRESS.md` and untracked `.specify/`, `AGENTS.md`, `specs/`, and handoff folder. | PASS |
| Visible local copy | Desktop and 375px local views show repeal power and preserved history. Expected unpushed-branch remote-file 404s keep this from being a production result. | PASS offline / BLOCKED live |
| Formatting/parsing | 58 Python tests, 27 Node tests, 66-requirement coverage, Python/API/HTML parse, shell syntax, and `git diff --check` pass. | PASS |

Known boundary: this is source/fixture review, not evidence that Upstash, OpenRouter,
Upload-Post, Vercel, `/human`, the VPS timer, or the X profile behave correctly in
production. Those rows remain BLOCKED in the production matrix.
