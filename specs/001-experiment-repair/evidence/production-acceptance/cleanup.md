# Production Acceptance Cleanup Receipt

**Run:** `run-20260721-current`
**Cleanup result:** PASS for the approved Crabbox lease and test-run scope;
full product acceptance remains FAIL.

- Coordinator lease `cbx_c2769e5ab363` was released.
- Coordinator status after teardown: 0 active leases.
- Direct Hetzner status after teardown: 0 matching servers and 0 matching SSH
  keys.
- New-infrastructure spend: approximately `$0.01` against the `$2` maximum.
- No production submissions or test records were created because `/human` and
  the required submission surfaces are absent on the deployed site.
- No X action was performed.
- Production configuration, canonical state, deployment, and loop state were
  not changed by this run.

The full product cleanup row remains FAIL because the undeployed site cannot
prove Redis queues, delivery uniqueness, historical ledgers, the rolling
last-ten average, provider/Vercel warnings, or the approved failure-mode restore
path through its visible UI. This receipt passes only the cleanup actually
created by the approved as-is run; it does not waive those later checks.

Machine-readable receipts are in `run-20260721-current/coordinator-cleanup.json`,
`run-20260721-current/hetzner-cleanup.json`, and
`run-20260721-current/spend.json`.
