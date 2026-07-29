# Backlog Repair — G15 Live Preflight

Date: 2026-07-29 WITA
Status: `PLANNED_STOP`

## Read-only production receipt

- VPS checkout: clean `main` at
  `b328f75ef1141784608d019fbc19b0d6e70596d0`, matching `origin/main`
- Canonical turn: 1139
- `language-loop.timer`: active, enabled; next scheduled event read back as
  2026-07-29 11:45 WITA
- `language-loop.service`: inactive between runs
- Current Vercel Production deployment:
  `dpl_3jLy3U5xWpUwnqUvGwSBQKgLvMfJ`, Ready, serving
  `https://alanguagealltheirown.com`
- Open human-review ids:
  `ask-683-b`, `ask-689-b`, `ask-692-b`, `ask-695-b`, `ask-821-b`

## Target

Release the reviewed backlog repair, apply only the hash-bound legacy-motion
migration, answer the five duplicate deadlock questions with one verified
diagnostic, resume the loop, and verify normal legislative progress.

This gate does not authorize semantic rulebook cleanup, a change to any adopted
rule, a workbook-cost-model change, X activity, DNS, credentials, or unrelated
production work.

## Immutable migration boundary

- Source rulebook:
  `57fbf58ea571eb6de76059e46da5ceb3eb918f6f8c047e7b23a8d01e46c85606`
- Replacement:
  `1788e0df19def49b8f8b7b1e6cfc4cd37732d99ec5a78231fdddb9786d40ce93`
- Exact diff:
  `c5d7b4df840ec060c90bc23c7c6c67382e28422289fa4e0ac413be26d8468698`
- Adopted records:
  `26aa8a6bcd62e024f92ede9e4fa33b27ec1860789b08def73a16ee963a4c5554`
- Adopted language:
  `cbd9f1aee46e67ba16e02d4613b12671bb111426ff9e08e391415898cbdf8272`
- Expected state transition: 69 proposed + 7 reverted become historical;
  23 adopted records remain exact; pending repeals remain zero.

Application fails closed if any source, replacement, diff, approval, adopted
record, language hash, or pending-repeal invariant differs.

## Verified diagnostic for the human-review backlog

`rule-054` is adopted. The phrase `rule-054-revised` was prose, but the parser
normalized it to `rule-054`, so votes against it correctly returned
`settled_or_ineligible_motion`. Separately, 69 legacy proposed records kept the
one-open guard true, causing new `PROPOSE` and `REPEAL` motions to return
`proposal_already_open`. There is no automatic timeout or proposer-withdrawal
path. The reviewed repair archives only legacy proposed/reverted records,
preserves all 23 adopted rules, and allows normal agent governance to resume.
The 23-rule language is not being declared final.

The five named open questions above must each receive this same factual answer
through the authenticated human-review action, preserving their original ids
and exact-once delivery.

## Serialized runway

1. Resolve the final reviewed feature commit after rebasing onto current
   `origin/main`; rerun all offline tests.
2. Capture the current VPS commit, timer state, canonical rulebook hash, adopted
   record/language hashes, collaboration ids, and rollback snapshot.
3. Verify the rulebook still equals the source hash and has zero pending
   repeals; otherwise stop without applying.
4. Under one exact approval, pause `language-loop.timer`, merge the reviewed
   branch through the repository release path, and sync the paused VPS.
5. Create the external approval receipt bound to the migration kind and exact
   source/replacement hashes; apply the prepared bundle.
6. Verify zero open motions, exact adopted invariants, clean service code, and
   unchanged X-disabled state.
7. Answer only the five named duplicate human-review questions with the
   diagnostic above.
8. Deploy the route-label viewer change from the same reviewed commit.
9. Resume the timer. Observe the next Agent A proposal and Agent B settlement,
   plus the next internal lookup; stop and re-pause on any warning or invariant
   failure. The next naturally scheduled Conversation supplies live validation
   evidence without forcing an extra paid workbook-bearing run.

## Rollback

On any failure, keep or return the timer to paused, restore the exact pre-apply
rulebook snapshot and prior runtime commit, promote the prior Vercel deployment
if the viewer changed, verify canonical/public hashes, and do not retry outside
the approved envelope.

## Approval envelope

The final operator handoff must bind the reviewed branch tip, VPS commit
`b328f75ef1141784608d019fbc19b0d6e70596d0`, a fresh rollback snapshot, current
deployment `dpl_3jLy3U5xWpUwnqUvGwSBQKgLvMfJ`, and the five verified ids above.
The exact `APPROVE LIVE CHANGE:` phrase is supplied only after the final local
commit exists; a phrase containing placeholders is invalid.
