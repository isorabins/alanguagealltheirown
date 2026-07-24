# Production deployment and Crabbox smoke receipt

Date: 2026-07-23 WITA

## Authorized scope

Iso explicitly authorized merge of draft PR #1, standard Vercel Production
deployment, public alias verification, and one non-mutating Crabbox smoke test
on one CPX32 in `fsn1` with a three-hour TTL and a `$1` infrastructure ceiling.
No application credential, canonical-state, live-loop, or X action was allowed.

## Deployment

- PR #1 merged into `main` at `0cc16b5f21ad9c3a0d872755ac63675925ac1fa4`.
- The initial root-repository deployment had no public entry point and was
  replaced immediately by the correct `viewer/` deployment.
- Current Production deployment: `dpl_5AEUyzhuuHaZ6rxJzgFaGN8S6XVM`, Ready,
  `https://alanguagealltheirown-hld3acf7v-isorabins-projects.vercel.app`.
- Public readback after alias assignment: `https://alanguagealltheirown.com/`
  and `/human` both returned HTTP 200.
- Vercel SSO deployment protection was disabled under the explicit public-live
  approval so the Production aliases can be reached publicly.

## Non-mutating remote browser smoke

- Lease: `cbx_393b75870b8e` (`brisk-hermit`), CPX32 `fsn1`, three-hour TTL.
- The runner made only page loads, screenshots, one browser restart, and one
  read-only HTTP receipt; it created no application data.
- Recording: one inspected outer-desktop MP4, 180.000 seconds; browser restart
  count: 1.
- Matrix result: **FAIL (18/26 PASS)**. Public identity, adopted-language copy,
  suggestion surface, Conversation/Try It surfaces, desktop/375px display, and
  the unauthenticated Human Review sign-in surface passed.
- Rows 5–7, 12–13, 16–17, and 21 failed because the current Production state
  has no active cleanup/RESEARCH/ASK delivery, approved X results, duplicate or
  rate-limit state, or missing-research-evidence state. Those are the existing
  paused-loop and public-action gates, not failures of the deployed public
  routes.

Evidence is retained locally under
`/Users/isorabins/CrabboxEvidence/alato-production-smoke-20260723/`.

## Teardown

- Crabbox coordinator reports zero active leases.
- Released Hetzner server `154425730` returns HTTP 404; the isolated project
  has zero SSH keys.
- Coordinator usage after release: 4,503 runtime seconds and `$0.08` cumulative
  estimated infrastructure spend, within the approved `$1` final-run ceiling.

Production is publicly reachable. This smoke receipt is not a full Production
acceptance pass: the blocked live-loop and X gates remain open.
