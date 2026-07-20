# US1 Offline Evidence — Trust the Experiment

Result: **PASS (offline contract); production visibility not yet run**.

- `test_rulebook_views.py` proves ordinary language output includes the adopted rule and excludes proposed, rejected, and reverted text. It also proves only `proposal_trial_payload` can add one currently proposed rule under an explicit `proposal_trial` label.
- `test_judge_validation.py` publishes a score only for complete one-to-one coverage; missing, duplicate, nonnumeric, and out-of-range cases return invalid with no fidelity.
- `test_exam_evidence.py` proves a corpus receipt is tied to the language hash and does not mutate legacy rule scores.
- `rulebook.py` and Vercel `_lib.js` independently construct adopted-only payloads and stable version/hash values.
- Active-path search returned no references to the retired benchmark import, hook, fields, prompt copy, or public section.
- Historical per-rule scores remain in `state/rulebook.json` and are labeled legacy on the page; new ordinary results append to corpus evidence instead.
- Current last-ten passing exams remain turns 513–540 with average `token_delta_pct=-29.2` (29.2% savings). No production state or measurement file changed.
