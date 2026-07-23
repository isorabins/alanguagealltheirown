# Remote Forward-Test Receipt

Date: 2026-07-21 WITA

- Reusable skill structure and manifest validation: PASS.
- Project fixture on the disposable Crabbox X11 desktop: 26/26 PASS, 27
  numbered screenshots, one repository-runner browser restart.
- Outer recording: PASS; one continuous 300-second MP4 spans the browser close
  and relaunch without restarting the recorder.
- Crabbox proof bundle: PASS after WebVNC target and portal bridge checks.
- Cleanup: PASS; coordinator leases 0, Hetzner servers 0, provider SSH keys 0,
  WebVNC daemons 0.
- Evidence/secret audit: PASS; all required artifacts present, spend `$0.01`
  under the `$2` ceiling, no protected values or secret-shaped content found.

Canonical remote artifacts and independent receipts are in `../pilot/`; see
`../pilot/README.md`. The separate generic local visible-browser forward test is
in `local-generic/` and passed 3/3 with restart and final clean state.
