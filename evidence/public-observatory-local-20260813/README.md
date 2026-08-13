# Public Observatory local acceptance — 2026-08-13

## Issue #58

- Served the repository root at `http://127.0.0.1:8765/viewer/` and loaded the generated production-shaped `viewer/state.js` bundle.
- Desktop viewport: 1440 × 1000 CSS pixels; document width 1421, so no horizontal overflow.
- Mobile viewport: 375 × 834 CSS pixels; document and body width 356, no clipped interactive controls, no blank metrics, and the four exam stages resolve to one 323px column.
- Browser console: zero errors and zero warnings.
- The six metric help controls rendered as labelled buttons. The strict-savings explanation opened with `aria-expanded=true` and explained the valid strict-pass requirement.
- The language copy control copied 78,122 characters beginning with `LANGUAGE adopted-41056d608709 (118 adopted rules)` and announced `Copied all 118 adopted rules.`
- Visual inspection covered the paused clocks and truth banner, six metrics, canonical Agent A/B panes, strongest strict pass and latest strict failure, four-stage Latest Exam with all semantic evidence, six-message Conversation judgment, current adopted language, Recent Evidence, Experiment Status, newest/all Field Notes, and all six Lab Notebook categories.

Screenshots:

- `issue-58-desktop.png`
- `issue-58-mobile-375.png`
- `issue-58-mobile-375-exam.png`

## Issue #59

- Exercised the canonical `PublicExamProgressWriter` with deterministic provider-free fixtures through the same writer, validator, persisted JSON, polling, and terminal renderer used by a future scheduled exam.
- The completed local trace was bound to canonical turn 2400, benchmark B1, and adopted-language hash; its encoded response, decoded response, token totals, and final verdict matched the canonical Latest Exam exactly.
- The trace advanced through 40 safe receipts: boundary, benchmark, language, encoder start/complete, decoder start/complete, judge start, all 31 semantic-audit progress counts, and the final result.
- Python fixtures rejected unknown fields, skipped transitions, mixed exam identities, oversized text, credential-shaped text, prompt-shaped text, private-state text, raw exception text, regressing audit progress, and writes after terminal state.
- JavaScript fixtures rendered completed, interrupted, failed, stale, missing, malformed, and unavailable states without changing the verified Latest Exam.
- Browser acceptance at desktop and 375px showed `VERIFIED COMPLETE`, two sanitized artifacts, token totals, the verdict, no horizontal overflow, no clipped controls, and zero console warnings/errors. The trace log is keyboard-focusable and uses the locked dark scrollbar treatment.
- The browser only polls `state/public-exam-progress.json`; reaching zero cannot call an encode, decode, judge, or provider endpoint.
- The generated acceptance snapshot is intentionally untracked local state. It is not embedded in the public archive or presented as historical production execution.

Screenshots:

- `issue-59-trace-desktop.png`
- `issue-59-trace-mobile-375.png`
