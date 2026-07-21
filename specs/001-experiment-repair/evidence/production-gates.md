# Production Gate Receipts

## T107 — reviewed branch and draft PR

- Date: 2026-07-21 (WITA)
- Approved checkpoint: `d23dae416bdd22d4bb833f4adf297ceb82045136`
- Remote branch: `origin/codex/experiment-repair`
- Draft PR: https://github.com/isorabins/alanguagealltheirown/pull/1
- Base: `main`
- Verified PR head at creation: `d23dae416bdd22d4bb833f4adf297ceb82045136`
- Authorized continuation: scoped T108–T117 commits may update this same draft PR.
- Excluded: merge, push to `main`, product deployment or mutation, DNS, X, and public actions.

Verification used both `gh pr view 1` and `git ls-remote`; both reported the
approved checkpoint as the remote head.

## T115–T117 — isolated Crabbox pilot

- Date: 2026-07-21 (WITA)
- Exact live-change approval: received for the isolated workers.dev coordinator,
  one Hetzner CPX32 Germany lease, eight-hour TTL, and `$2` maximum.
- Pilot result: PASS; remote fixture 26/26, continuous cross-restart video PASS,
  proof bundle PASS, reusable skill validation PASS.
- Cleanup: zero coordinator leases, zero matching Hetzner servers and SSH keys.
- Spend: Crabbox metered `$0.01`; eight-hour reservation estimate `$0.56`; the
  provider invoice had not posted at closeout.
- Production boundary: no product deploy, loop/state/credential/X action, DNS
  change, merge, or push to `main` occurred.
