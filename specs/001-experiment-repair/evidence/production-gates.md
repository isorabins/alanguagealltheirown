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

## T120 attempt 2 — approved branch push and safe cleanup stop

- Date: 2026-07-21 (WITA)
- Draft PR 1 remained open/draft; its verified head advanced only to the
  approved feature commit `b18a262dc99748381fb65f31dc7f3afec37163ca`.
- One approved additional DeepSeek V3.2 call ran against only the immutable
  turn-650 copy. Exact source coverage failed; no Kimi call ran.
- Actual attempt-2 spend: `$0.000876983`; cumulative G4 spend:
  `$0.012418691`, below the `$0.12` ceiling.
- Production remained paused, clean, and byte-identical at the approved commit
  and rulebook hash. T120 remains open at the repeated-blocker stop.

## T144–T148 — offline structural coverage repair

- Date: 2026-07-21 (WITA)
- Spec Kit contract checkpoint: `e78bc6a543cdf3def174ac28bb0e2473b00a46a1`.
- Tested implementation checkpoint: `81066d8793a69442b9a5e8bf1cb1ca915d99fba1`.
- The production-shaped strict schema requires exactly all 23 adopted source
  ids and forbids extras. Local compilation derives exact ordered coverage and
  rejects missing/extra assignments plus unknown/orphan/duplicate groups before
  Kimi. Python 65/65, JavaScript 27/27, and contract coverage 148/148 pass.
- Protected execution preflight made zero provider calls and passed with a
  conservative `$0.032840330` two-call projection, below the proposed `$0.10`
  additional and `$0.12` cumulative ceilings.
- Read-only closeout verified the production timer and service inactive, clean
  VPS `main` still at `75cd45704f3fd74906c3ee4edb53e81187b6ff2a`, and
  rulebook SHA-256 still
  `5938df47b587aabfb9fe7231c07d12b315a3ac3f7bdcbfee73b076fe219e4933`.
- No feature push, provider call, production change, deployment, credential
  action, or X action occurred. T120 remains open. The next lawful action is one
  combined exact phrase authorizing the final local commit's push to the same
  draft PR and one schema-bound A call plus conditional B audit.
