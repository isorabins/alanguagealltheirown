# Backlog Repair — Offline Verification

Date: 2026-07-29 WITA

## Approved scope

Iso approved three repairs after a fast Wayfinder pass:

1. terminalize legacy proposal state without changing the 23 adopted rules;
2. route internal questions to project evidence, with evidence misses going to
   `ASK Iso` and never to web;
3. align the Conversation judge prompt with its validator.

The workbook/rulebook cost model is unchanged.

## Baseline and migration rehearsal

- Clean feature worktree branch: `codex/alato-backlog-repair`
- Worktree baseline: `e6e5525` (`turn 1138`)
- Latest fetched `origin/main` during verification: `5854eb0` (`turn 1146`)
- Latest remote canonical rulebook snapshot hash:
  `57fbf58ea571eb6de76059e46da5ceb3eb918f6f8c047e7b23a8d01e46c85606`
- Remote rule counts: 23 adopted, 69 proposed, 7 reverted, 0 pending repeals
- Prepared replacement hash:
  `1788e0df19def49b8f8b7b1e6cfc4cd37732d99ec5a78231fdddb9786d40ce93`
- Exact diff hash:
  `c5d7b4df840ec060c90bc23c7c6c67382e28422289fa4e0ac413be26d8468698`
- Adopted-record hash:
  `26aa8a6bcd62e024f92ede9e4fa33b27ec1860789b08def73a16ee963a4c5554`
- Adopted-language hash/version:
  `cbd9f1aee46e67ba16e02d4613b12671bb111426ff9e08e391415898cbdf8272`
  / `adopted-cbd9f1aee46e`

The frozen production-shaped rehearsal terminalized 69 proposed and 7 reverted
records, left zero open motions, preserved every adopted record exactly, and
allowed a new Agent A proposal followed by Agent B adoption. The transform is
idempotent. Preparation/application reject source drift, artifact tampering,
wrong approval kind, and any pending repeal.

## Research and lookup result

The router passed seven known internal-question regressions, including turn,
rule, harness-error, pending-repeal, and alias-use questions. Every one returned
bounded canonical project evidence with `web_search_requests=0` and `cost_usd=0`.
An empty project corpus created one stable correlated `ASK Iso` record on two
processing attempts. One outward-looking fixture used the existing bounded web
tool, while malformed non-JSON prose with a citation was recorded as
`no_evidence`.

Project evidence is capped at 24,000 characters and explicitly labeled as data,
not instructions.

## Conversation result

The judge now receives `numbered_requirements` and is instructed to return one
integer `id` plus boolean `pass` row per requirement. The production-shaped
loop seam produced four complete rows and the existing validator returned
`valid`. Missing, duplicate, and malformed rows remain invalid.

The five historical scheduled Conversation artifacts remain preserved and
invalid; they are not rewritten.

## Human answer repair

Read-only Production logs showed that Iso's six visible clicks reached
`POST /api/human-action` after the non-sliding session expired and all returned
`401`. The stale page swallowed the errors and kept the old inbox visible.

The repaired local browser flow now turns an expired session into an explicit
login prompt, preserves the draft through re-authentication, shows a visible
submitting/error state, and exposes an accepted command as `answer_pending`
with the exact answer. The answer remained visible after a full page reload.
Screenshots and the evidence matrix are in
`evidence/backlog-repair/human-answer-repair/`. Production remains unchanged
until the combined live gate is approved.

## Verification

- `python3 -m unittest discover -s tests/python -p 'test_*.py'`
  — PASS, 85 tests
- `node --test tests/js/*.test.js`
  — PASS, 31 tests
- `python3 tests/acceptance/check_contract_coverage.py`
  — PASS, 89 requirements and 185 sequential tasks
- Focused migration, research, prompt, and Conversation tests
  — PASS, 19 tests
- Python compilation and `git diff --check`
  — PASS
- Secret-pattern scan across changed paths
  — PASS, no matches

No canonical `state/` file, production service, provider, credential, timer, or
human-review record was changed. This is offline evidence, not production
acceptance.
