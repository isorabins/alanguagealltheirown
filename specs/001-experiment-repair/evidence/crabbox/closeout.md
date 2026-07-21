# Crabbox Acceptance-Infrastructure Closeout

Date: 2026-07-21 WITA

## Result

T108–T117: **PASS**. Crabbox v0.40.0, the repository-owned runner, the reusable
local skill, the off-production fixtures, the isolated remote desktop, the
continuous restart video, proof collection, spending enforcement, secret audit,
and teardown met their contract.

The full production acceptance result remains **BLOCKED / NOT RUN**. The pilot
approval expressly excluded product deployment, production loop/state,
product-credential creation, X actions, and production acceptance mutations.
No overall product PASS is claimed.

## Verified facts

- Remote repository fixture: 26/26 PASS; 27 numbered screenshots; one browser
  process restart.
- Outer evidence: one unbroken 300-second H.264 MP4 at 1920x1080 and 15 fps.
- Disposable runtime: one CPX32 in `fsn1`, 738 seconds, released.
- Cleanup: coordinator active leases 0; matching Hetzner servers 0; matching
  provider SSH keys 0; WebVNC daemon stopped.
- Cost: Crabbox metering `$0.01`, below the `$2` ceiling. The maximum eight-hour
  reservation was `$0.56`; the Hetzner invoice had not posted at closeout.
- Cloudflare: free workers.dev coordinator retained idle, prewarm 0, active-lease
  cap 1, monthly cap `$2`, no paid plan and no DNS changes.
- Evidence audit: required artifacts present; no exact protected values or
  secret-shaped content found; credential entry absent from media.
- Spec Kit convergence: 78 requirement/success references and all 143 existing
  tasks checked; no untracked contract gap and no new convergence task required.

During setup, a malformed newly created pilot Cloudflare token was detected and
revoked before deployment. It was replaced with a Workers-Scripts-only token;
the replacement value is stored only in the protected external profile and
Bitwarden. No token value is present in this repository or evidence bundle.

## Reuse and next gate

The canonical local skill is
`/Users/isorabins/.codex/skills/run-crabbox-human-tests/`. Future runs reuse the
free idle coordinator and create a paid Hetzner machine only for the run, then
destroy it. This is cheaper long-term than retaining a server and preserves the
coordinator-owned TTL/cap/cleanup guarantees.

The next project action is T118 read-only production runway recheck. T119 and
later gates still require their exact immutable target phrases; this closeout
does not authorize them.
