# Structured Legislative Protocol Requirements Checklist

**Purpose**: Review the Phase 24 requirements as a compact backend release
contract before implementation.

**Created**: 2026-07-29 WITA

## Requirement Completeness

- [x] CHK001 Are requirements defined for the complete model-output path from state-specific schema through local validation, state transition, persistence, and next-request grounding? [Completeness, Spec §FR-062–065]
- [x] CHK002 Are requirements defined separately for malformed structure, legislatively illegal actions, successful actions, and later scheduled recovery? [Coverage, Spec §FR-063–065]
- [x] CHK003 Are migration requirements defined for old events without rewriting or inventing historical data? [Completeness, Spec §FR-066]
- [x] CHK004 Are exact provider-cost accounting and the boundary of the application tripwire documented without implying a provider-side limit? [Clarity, Spec §FR-067]

## Requirement Clarity

- [x] CHK005 Is the distinction between a stable Pydantic envelope family and state-specific per-turn permitted variants unambiguous? [Clarity, Spec §FR-062–063]
- [x] CHK006 Is structural retry bounded by an exact count with an exact no-mutation and same-actor outcome? [Measurability, Spec §FR-064]
- [x] CHK007 Are post-state receipt fields and their authority over model prose explicitly enumerated? [Clarity, Spec §FR-065]

## Requirement Consistency

- [x] CHK008 Do the structured-action requirements preserve the existing A/B role authority and single-writer state-machine boundary? [Consistency, Spec §FR-062–065]
- [x] CHK009 Do cutover requirements preserve append-only history while allowing a new authoritative rendering projection? [Consistency, Spec §FR-066]
- [x] CHK010 Are live-agent governance changes distinguished from prohibited manual rule/state edits? [Consistency, Spec §FR-068]

## Acceptance Criteria Quality

- [x] CHK011 Can schema legality, retry behavior, receipts, legacy preservation, historical failure replay, and exact costs each be independently measured? [Acceptance Criteria, Spec §SC-029–034]
- [x] CHK012 Is the live acceptance boundary limited to the B/test/A canary, exact spend ceiling, repository/service health, rollback, and explicit prohibited surfaces? [Scope, Plan §G16]
