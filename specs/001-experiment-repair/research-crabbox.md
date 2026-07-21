# Crabbox Acceptance Infrastructure Research

**Checked**: 2026-07-21 WITA

**Decision**: Use pinned Crabbox v0.40.0 with one isolated Cloudflare Durable
Object coordinator and at most one Hetzner CPX32 Germany X11 desktop lease.
Keep the product-specific browser journey and acceptance oracle in this
repository; keep generic provisioning, recording, proof collection, env
allowlisting, and teardown in the local `run-crabbox-human-tests` skill.

## Primary Sources And Pinned Reference

- Official repository: https://github.com/openclaw/crabbox
- Immutable release: https://github.com/openclaw/crabbox/releases/tag/v0.40.0
- Tag object: `83d090fd1456202012e73ecad606c81831219b54`
- Tagged commit: `47f8e45c9a13e50c40255e8312f16b1eed1b0003`
- macOS arm64 SHA-256:
  `cdb30721e8d82d9ae0f1be694eeacfa0ee5834023230d06f0e316f6016ae3f87`
- Pinned clean source/docs checkout:
  `/Users/isorabins/.codex/vendor-snapshots/openclaw-crabbox/v0.40.0`
- Snapshot receipt:
  `/Users/isorabins/.codex/vendor-snapshots/openclaw-crabbox/SNAPSHOT-v0.40.0.md`
- Official desktop commands: https://crabbox.sh/commands/desktop.html
- Official security model: https://crabbox.sh/security.html
- Pinned lifecycle source: `docs/features/lifecycle-cleanup.md`
- Pinned env source: `docs/features/env-forwarding.md`
- Pinned artifacts source: `docs/features/artifacts.md`
- Pinned Hetzner source: `docs/providers/hetzner.md`
- Cloudflare pricing: https://developers.cloudflare.com/workers/platform/pricing/
- Hetzner pricing:
  https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/

No downloaded repository script or binary was executed during research.

## Source-Level Findings

### Outer Recording

The Linux desktop recorder starts remote FFmpeg with X11 `x11grab` and streams
fragmented MP4 over SSH. It records the whole X11 desktop independently of the
browser process, so an ordinary browser close and relaunch remains inside one
outer recording. Recording has no audio and requires the SSH/local recorder
process to remain connected. Wayland and macOS desktop recording are not the
selected path.

The proof bundle can contain metadata, screenshot, diagnostics, MP4, and contact
sheet. The implementation creates owner-only artifact paths, but captured
content is not guaranteed to be secret-scrubbed; manual evidence inspection is
therefore required.

### Browser And Credentials

Crabbox can prepare a browser and lease-scoped profile but does not perform
project login migration. The project runner must own Playwright storage state or
short-lived login behavior. Full personal browser profiles are forbidden.

Environment forwarding is opt-in by variable name. A protected env profile may
be copied to the runner only for explicitly allowlisted names and removed after
the run. This still grants secrets to the remote runner; the manifest must use
the smallest possible allowlist, and recordings must pause or obscure secret
entry.

### Lifecycle And Cost

Direct Hetzner `--ttl` metadata is not a durable termination guarantee: cleanup
still depends on a cleanup process running. That does not satisfy the pilot's
fail-closed cleanup requirement if the Mac, shell, or recording process dies.

The smallest durable path is the official coordinator using one Cloudflare
Worker/Durable Object. It can enforce one active lease, reserved monthly spend,
TTL alarms, cleanup retries, and provider ownership without a portal, custom
domain, OAuth application, or published artifact service.

The selected Hetzner CPX32 Germany rate is approximately EUR 0.0673/hour before
minor tax/IP extras. An eight-hour lease is approximately EUR 0.54. The approved
maximum new-infrastructure spend is `$2`, not a target. Preparation must happen
locally so the paid lease exists only for executable remote proof or the later
approved production run.

### Provider Choice

- **Selected**: coordinator-managed Hetzner CPX32 Germany, Linux X11.
- **Rejected**: direct Hetzner, because no durable cleanup owner survives local
  failure.
- **Rejected**: direct GCP, because the official provider path does not support
  the required Linux desktop/browser/code mode despite provider-native maximum
  duration controls.
- **Rejected**: local container/Xvfb as the final pilot path, because it can
  produce cross-browser-restart video but does not create the requested remote
  failure/isolation boundary.
- **Not needed**: coordinator portal, custom DNS, artifact publication, multiple
  providers, or Semaphore.

## Dependency Safety Decision

**Risk**: YELLOW before installation.

Evidence checked:

- GitHub marks the immutable release and tagged commit verified.
- The release publishes asset digests and provenance metadata.
- No GitHub Security Advisory was published at research time.
- Open issue https://github.com/openclaw/crabbox/issues/1176 reports a
  Semaphore-provider pagination path that may expose its token to a malicious
  target. This pilot will not configure Semaphore.
- The release is recent, the CLI is a global executable, and its purpose is to
  provision machines and execute remote code. Those residual capabilities keep
  the review YELLOW even with a verified checksum.

Installation guardrails:

1. Repeat release/advisory/issue checks immediately before installation.
2. Install only the exact macOS arm64 v0.40.0 asset after verifying its SHA-256.
3. Do not use `curl | sh`, unpinned `brew install`, repository bootstrap scripts,
   `npx`, or another execute-on-download path.
4. Run version/help checks without unnecessary secrets in the environment.
5. Exclude Semaphore and fail closed on provider/config drift.

## Local Reality At Planning

- Crabbox is not installed.
- FFmpeg 8.1.1, Node 22.23.1, npm 10.9.8, pnpm 10.8.0, and Python 3.14.5 are
  available.
- The repository has no package manifest for the production acceptance runner;
  it will receive an isolated exact-pinned package/lockfile.
- GitHub, Vercel, and VPS read-only access are available.
- The cached Wrangler OAuth expiry is `2026-05-12T11:19:04.486Z`; current
  Cloudflare access is unproved.
- No Cloudflare or Hetzner provider secret name was found in Bitwarden metadata.
- No Hetzner CLI/token was found locally.
- Bitwarden Secrets Manager CLI 2.0.0 is available and is the required secret
  store; values are never printed or written into project/skill files.

## Acceptance Oracle

The off-production forward test passes only when:

1. exact provider/account/coordinator/machine/region/TTL/cap manifest checks pass;
2. one outer MP4 visibly spans browser close and relaunch;
3. screenshots and proof files map to their named claims;
4. no credential value appears in files, logs, command history, or media;
5. coordinator and provider independently report zero active pilot leases;
6. actual new-infrastructure spend is known and no more than `$2`; and
7. the local skill passes `quick_validate.py` and repeats the fixture workflow
   without this project's credential names or acceptance assumptions.

Anything weaker is `FAIL` or `BLOCKED`, never a partial PASS.
