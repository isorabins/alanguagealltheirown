# Crabbox Pilot Evidence Guide

Result: **PASS for the off-production Crabbox infrastructure pilot.** This is
not a production-product acceptance result.

## Primary evidence

- `00-cross-turn-workflow.mp4`: single continuous 300-second, 1920x1080 H.264
  outer-desktop recording.
- `00-cross-turn-workflow.event-contact.png`: review sheet for video seconds
  41–50, showing browser appearance, close/restart, reappearance, and desktop /
  375px progression in the same recording.
- `runner/matrix-results.json`: repository-owned result, 26/26 PASS and one
  browser restart.
- `runner/01-*.png` through `runner/27-*.png`: numbered visible-row evidence and
  final clean state.
- `crabbox-proof/`: Crabbox doctor, run metadata, logs, screenshot, and WebVNC
  status collected from the same lease.

## Independent receipts

- `coordinator-deploy.json`: exact free workers.dev deployment and limits.
- `lease-lifecycle.json`: provider, machine class, TTL, runtime, runner, and
  release identity.
- `video-inspection.json`: media properties, hashes, and restart review.
- `spend.json`: metered and reserved-cost facts against the `$2` ceiling.
- `coordinator-cleanup.json` and `hetzner-cleanup.json`: independent zero-resource
  readbacks after teardown.

The evidence audit found every required screenshot, a passing matrix, restart
continuity, proof files, zero active resources, spend within cap, and no exact
protected values or secret-shaped content. Credential entry was never recorded.

## Boundary

The retained Cloudflare Worker is an idle coordinator on Workers Free at its
workers.dev hostname. No DNS was changed. The disposable Hetzner lease was
released. Product deployment, production loop/state, product credentials, X,
and the 26-row production acceptance run remain untouched and require T118+
immutable live-gate approvals.
