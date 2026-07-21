# Crabbox Dependency Safety Review

## T108 — Crabbox v0.40.0

Risk: **YELLOW**

- Package: official `openclaw/crabbox` release `v0.40.0` for macOS arm64.
- Requested action: install the standalone release executable, not Homebrew,
  `curl | sh`, `npx`, or any repository script.
- Release: https://github.com/openclaw/crabbox/releases/tag/v0.40.0
- Tag object: `83d090fd1456202012e73ecad606c81831219b54`
- Tagged commit: `47f8e45c9a13e50c40255e8312f16b1eed1b0003`
- GitHub verified both the annotated tag signature and commit signature.
- Published: 2026-07-19T17:46:56Z; review repeated on 2026-07-21.
- Official archive SHA-256: `cdb30721e8d82d9ae0f1be694eeacfa0ee5834023230d06f0e316f6016ae3f87`.
- Downloaded archive matched the release API digest, `checksums.txt`, and the
  final notarized payload entry in `provenance.json`.
- The provenance binds repository, tag, commit, version, platform, architecture,
  Apple team `FWJYW4S8P8`, hardened runtime, timestamps, and notarization.
- Archive inventory contained only `crabbox` and the optional
  `crabbox-apple-vm-helper`; only `crabbox` was installed for this pilot.
- `codesign --verify --deep --strict` passed. `spctl -t exec` described the raw
  command-line executable as valid code but not an app; this is not treated as
  an application-bundle Gatekeeper approval.
- GitHub repository security-advisory API returned no published advisories.
- OSV's commit query for the tagged commit returned no entries.

Open issue #1176 is a confirmed URL-construction hardening gap in only the
Semaphore provider. The maintainer classifies it as defense-in-depth because
the pagination header comes from Semaphore's authenticated response, but an
affected request can disclose a Semaphore token if that header is influenced.
This pilot prohibits Semaphore completely and has no Semaphore credential or
configuration, so that path is unreachable.

Recommendation: proceed only with the exact verified binary and the approved
Cloudflare coordinator plus Hetzner provider. Keep Semaphore absent, keep
provider tokens out of argv/repo/media, enforce the `$2`/eight-hour limits, and
tear down through both coordinator and provider.

Residual risk: Crabbox is a recent privileged remote-execution binary with
cloud provisioning and SSH capabilities. A correct checksum proves artifact
identity, not benign behavior; all live use therefore remains inside the
isolated, capped, fail-closed pilot.

## T111 — Playwright

Risk: **GREEN** for the selected minimal package.

- Selected: `playwright-core@1.61.1`, exact-pinned in the isolated acceptance
  package and lockfile.
- Published: 2026-06-23T19:49:00.061Z (more than 27 days old at review).
- Registry repository: `https://github.com/microsoft/playwright.git`.
- License: Apache-2.0; established Microsoft maintainers unchanged.
- Tarball integrity:
  `sha512-h7Qlt6m4REp25qvIdvbDtVmD4LqVXfpRxhORv9L0jzETM05p4fuPJ3dKyuSXQxDSbXnmS79HAgi9589lGSpLkg==`.
- Registry signature and SLSA provenance attestation are present and passed
  `npm audit signatures`.
- The exact version has no package lifecycle scripts or dependencies.
- GitHub's repository advisory API and OSV exact-version query returned no
  advisory; `npm audit` found zero vulnerabilities.
- Install command used `--ignore-scripts --save-exact`; `.npmrc` keeps lifecycle
  scripts disabled.

The broader `@playwright/test` package was deliberately not retained. Its
optional `fsevents@2.3.2` dependency has a native install hook; although the
hook was suppressed, removing that unnecessary dependency is safer. The runner
uses Node's built-in test framework plus `playwright-core` and the browser that
Crabbox provisions.
