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
