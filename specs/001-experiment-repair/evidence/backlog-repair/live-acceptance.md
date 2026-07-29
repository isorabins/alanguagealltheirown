# Backlog Repair — G15 Live Acceptance

Date: 2026-07-29 WITA
Approval: `APPROVE LIVE CHANGE: alato-backlog-repair-20260729-857bb2d-g15`
Status: `PLANNED_STOP`

## Release and rollback

- Reviewed feature commit: `857bb2df985b05612150d6c65cd8c7dde546fc5a`
- Release PR: <https://github.com/isorabins/alanguagealltheirown/pull/7>
- Merge commit: `0c6d1620443f41e3de219614eda5df28993f743c`
- Rollback snapshot:
  `/root/alato-rollbacks/20260729-857bb2d-g15/state.tar.gz`
- Rollback snapshot SHA-256:
  `6b3840c84d9ac1a5f8e73e4239fddb8e808ced31a8b7c3eeb2b1e78755d3f482`

## Legacy motion repair

The hash-bound migration applied once and returned `idempotent_retry: false`.

- Applied state commit: `1ffb5052b5c7041e64f715a3a71d781d2961d420`
- Canonical rulebook SHA-256 after application:
  `1788e0df19def49b8f8b7b1e6cfc4cd37732d99ec5a78231fdddb9786d40ce93`
- State after application: 23 adopted, 0 proposed, 0 reverted,
  76 historical, 24 rejected, 0 pending repeals
- Adopted-record hash:
  `26aa8a6bcd62e024f92ede9e4fa33b27ec1860789b08def73a16ee963a4c5554`
- Adopted-language hash:
  `cbd9f1aee46e67ba16e02d4613b12671bb111426ff9e08e391415898cbdf8272`

The 23 adopted rules remained exact. Only the 69 legacy proposed and 7 reverted
records became historical.

## Human answer path

Production deployment `dpl_EytqptsgKTxvEmweXD2TCBcQ7bz7` reached `Ready` and
served `https://alanguagealltheirown.com`.
The live `/human` HTML SHA-256 exactly matched `viewer/human.html` at the
reviewed feature commit:
`3222f2ce37d36867f18c563e35ff18518c629de49f11f3606676df1db15b2cb5`.

The authenticated production `/human` surface showed all five named questions.
Each exact diagnostic answer produced a visible `answer_pending` success state.
After the real Refresh action, all five answers remained visible.

Read-only deployment logs independently recorded:

- exactly five `POST /api/human-action` responses with status `202`;
- authenticated `GET /api/human-inbox` responses with status `200`; and
- every accepted request on deployment `dpl_EytqptsgKTxvEmweXD2TCBcQ7bz7`.

Screenshots:

1. `human-answer-repair/01-live-authenticated-five-asks.png`
2. `human-answer-repair/02-live-first-answer-pending.png`
3. `human-answer-repair/03-live-five-answers-pending.png`
4. `human-answer-repair/04-live-five-answers-persisted.png`
5. `human-answer-repair/05-live-four-answers-recorded.png`
6. `human-answer-repair/07-live-five-answers-recorded.png`

## Loop uptake

Starting the persistent timer triggered turn 1147 immediately, then returned
to its normal 15-minute schedule. The first bounded courier pull imported four
answer commands exactly once, changing `ask-683-b`, `ask-689-b`, `ask-692-b`,
and `ask-695-b` from `awaiting_iso` to `answered` with `answer_turn: 1147`.
`ask-821-b` remained queued for the next pull because the courier's intentional
per-queue limit is four.

Turn 1147 completed and pushed as commit `969ec91`. Agent A made no motion
because its response still relied on the pre-repair deadlock in its recent
conversation window. It asked a project-internal turn question using the
`RESEARCH` label.

Turn 1148 completed and pushed as commit `2c66c84`. It imported the fifth
answer, delivered `ask-683-b` to Agent B, and left all four remaining answers
eligible for later exact-once delivery. The authenticated human page then
showed all five as recorded; `ask-683-b` was `delivered` and the other four
were `answered`.

The turn-1147 internal question was classified as `route: project`, resolved
from 10 bounded project records, and recorded with zero prompt tokens, zero
completion tokens, zero web-search requests, and zero cost. Agent B's turn-1148
response explicitly acknowledged the diagnostic and that governance can resume.

Turn 1149 was a normal corpus exam: fidelity was 100%, while body tokens
expanded from 445 to 674 (`+51%`) because the encoder defined 19 aliases and
duplicated the narrative in directive lines. Agent B's turn-1148 internal
question was also classified as `route: project`, answered from 10 bounded
project records, and recorded with zero model tokens, zero web requests, and
zero cost.

Turn 1150 proved live governance was writable again. Agent A's
`REPEAL: rule-072` motion was accepted with reason `repeal_proposed`; it was not
rejected as `proposal_already_open`. The adopted-language hash remained exact at
`cbd9f1aee46e67ba16e02d4613b12671bb111426ff9e08e391415898cbdf8272`.

## Planned stop

The timer was paused after turn 1150 at commit `7354a6c`. Agent A chose a repeal
of adopted alias rule 072 rather than an add proposal. Letting Agent B vote
could reduce the 23-rule adopted language, while G15 explicitly excludes any
change to an adopted rule. Both the timer and service read back inactive; the
VPS worktree was clean and matched `origin/main`.

The accepted repeal proposal proves the legacy one-open guard is gone. A live
settlement and the naturally scheduled Conversation artifact now require a
separate approval that permits normal governance to change an adopted rule.
The Conversation validator remains production-shaped offline PASS but live
unverified.
