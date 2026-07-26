# Public viewer visual repair — acceptance matrix

Date: 2026-07-26 WITA
Branch: `codex/language-visual-repair`
Base: `ea6db6aaefc87e52ba038b11c9b0d048a72e9c3e`
Mapped contract: T049, T067, T093; FR-030

## Definition of done

The public viewer preserves its existing research-artifact identity while:

1. rendering at 1280px and 375px without document-level horizontal overflow;
2. showing collaboration as a compact current-status surface with one canonical
   open question and collapsed research/history;
3. rendering the latest Conversation judgment as reader-facing outcome and
   requirement rows, with raw evidence collapsed;
4. showing only the decision-relevant active proposal by default and collapsing
   repetitive proposal records;
5. keeping newest/decision-relevant content open while grouping reference
   material into a collapsed Lab Notebook;
6. providing readable small-text/link contrast and visible keyboard focus;
7. preserving the suggestion, Try It, agent panes, exam, and public-state
   behavior already covered by the existing frontend tests.

## Evidence matrix

| Evidence | Claim | Required visible cue | Read-only receipt | Status |
|---|---|---|---|---|
| `01-desktop-top.png` | Existing identity and live summary are preserved | title, timers, metrics, negotiation heading | local HTTP 200 | PASS |
| `02-desktop-status.png` | Collaboration is compact and decision-oriented | one status band, one canonical issue, collapsed research/history | DOM height and item counts | PASS |
| `03-desktop-conversation.png` | Conversation judgment is readable and contained | held-status label, outcome summary, requirement rows, collapsed raw evidence | document width = viewport | PASS |
| `04-desktop-proposals.png` | Only current proposal is open | one current proposal plus 68-record collapsed archive | proposed-record count | PASS |
| `05-mobile-top.png` | Core entry reflows at 375px | full-width title/metrics with no clipping | document width = viewport | PASS |
| `06-mobile-status.png` | Status and archives reflow without a text wall | single-column current status, collapsed details | document width = viewport | PASS |
| `07-keyboard-focus.png` | Keyboard users can see focus | visible gold focus ring on the suggestion textarea | active element receipt and CSS/static test | PASS |

## Additional evidence

| Evidence | Claim | Result |
|---|---|---|
| `08-lab-notebook-open.png` | Collapsed archive remains readable when deliberately opened | PASS; no horizontal overflow |
| `09-raw-judgment-open.png` | Raw JSON remains available without breaking document width | PASS; wrapped and contained |
| `browser-receipt.json` | Browser dimensions, containment, console, and focus receipts | PASS |

## Evidence guide

`01-desktop-top.png`
: Claim: the original title, live timers, metrics, and negotiation identity are
  preserved. Look for the full editorial header and two agent windows. Quality:
  strong.

`02-desktop-status.png`
: Claim: collaboration is now one compact decision surface. Look for one
  operator issue, `1 current`, seven research notes, and the structured
  Conversation immediately below. Quality: strong.

`03-desktop-conversation.png`
: Claim: the invalid judgment is presented honestly and readably. Look for
  `judgment held`, the outcome, four requirement rows, and two collapsed
  evidence controls. Quality: strong.

`04-desktop-proposals.png`
: Claim: proposal state no longer creates a page wall. Look for one latest
  unresolved proposal, `68 earlier unresolved records · collapsed`, and the
  collapsed Lab Notebook. Quality: strong.

`05-mobile-top.png`
: Claim: the entry reflows at an exact 375px browser layout. Look for the full
  title, timer pair, and wrapping metrics with no clipped content. Quality:
  strong.

`06-mobile-status.png`
: Claim: the status surface reflows to one column at 375px. Look for one
  operator-review issue and the collapsed technical question. Quality:
  acceptable with receipt; the in-app browser capture includes its own right
  gutter, while the DOM receipt proves page width equals viewport width.

`07-keyboard-focus.png`
: Claim: keyboard focus is visually obvious. Look for the gold outline around
  the suggestion textarea. Quality: strong.

`08-lab-notebook-open.png`
: Claim: archival material remains available on demand. Look for the opened
  research/methods archive below the main story. Quality: strong.

`09-raw-judgment-open.png`
: Claim: technical JSON remains readable without horizontal overflow. Look for
  wrapped JSON below the open raw-evidence control. Quality: strong.

## Acceptance loop

- Repair loops used: 1.
- Visible journey: local public viewer load → compact current status →
  structured held judgment → collapsed proposal history → 375px reflow →
  visible focus → archive/raw-evidence expansion.
- Browser console: no warnings or errors.
- External writes: none.
- Production: not touched.

## Preflight

| Dependency | State | Evidence |
|---|---|---|
| Clean worktree | available | worktree created from current `origin/main` |
| Public state fixture | available | repo `state/` files and `viewer/state.js` |
| Static local server | available | repo uses plain HTML/JS; no framework install |
| In-app browser | available | used successfully for the live audit |
| Production deployment | planned stop | exact live-change approval required |
| External writes/test submissions | not needed | repair can be verified read-only |
| Cleanup | not needed | no disposable public data will be created |
