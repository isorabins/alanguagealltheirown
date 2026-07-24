# Launch-First Core Activation Preflight

Date: 2026-07-24 WITA

Status: **APPROVED — completed**

Exact approval:

`APPROVE LIVE CHANGE: launch-alato-core-with-existing-rulebook-20260724-l4v8`

## Approved outcome

Activate the repaired core experiment with the existing rulebook. Configure the
Production collaboration, human-review, and separately capped public-inference
dependencies; keep X disabled; sync the paused VPS to reviewed `main`; deploy
from `viewer/`; resume and verify one normal production turn.

Cleanup generation/application, X actions, DNS, destructive history changes,
and a full hostile/failure Production acceptance run are excluded.

## Verified starting state

- GitHub `main`: `0cc16b5f21ad9c3a0d872755ac63675925ac1fa4`.
- Public `/` and `/human`: HTTP 200.
- Current rollback deployment:
  `dpl_5AEUyzhuuHaZ6rxJzgFaGN8S6XVM`, Ready.
- VPS: clean `main` at
  `75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, matching its upstream.
- `language-loop.timer`: enabled but inactive.
- `language-loop.service`: inactive.
- Last canonical turn: 650.
- Rulebook SHA-256:
  `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
- Conversation SHA-256:
  `694b353861d1bbda12e3dafa4d6cc68ffd4306393f59075246c1ec56861882a5`.
- Tweet-state SHA-256:
  `12cebb0cbe043c4abe4279597af20fb1d03f6a684b7d9ecd1c0c688814255421`.
- Meta SHA-256:
  `0176bbb2cac25a52afa4808bdc2e0e3b5e00133a9685dc20680c07a6b48c2373`.
- The reviewed `main` tree has the same four canonical state hashes as the
  paused VPS.
- Current Vercel Production has only `OPENROUTER_API_KEY`; the required public
  key, human password, and Redis names are not yet targeted to Production.

## Fail-closed rules

- Any pre-resume canonical hash drift stops activation.
- Any wrong-root or unhealthy Vercel deployment rolls back to the deployment
  above.
- X is forced off before service start.
- Any first-turn service, provider, queue, duplicate, state, or invariant
  warning immediately re-pauses the timer.
- No cleanup bundle is generated or applied.
