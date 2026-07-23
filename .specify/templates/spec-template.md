# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

## Documentation Context *(mandatory)*

<!--
  ACTION REQUIRED: Before writing the spec, search bounded source-of-truth
  materials: repo docs, prior specs, architecture notes, runbooks, progress
  logs, user-provided docs, vendor handoffs, API contracts, and workspace
  indexes. Record the docs that shaped the contract. Do not include broad
  implementation research here unless it is already needed to define user
  scope, external behavior, safety, or acceptance.
-->

| Source | Type | Relevance | Key Constraint / Decision | Conflict Status |
|--------|------|-----------|---------------------------|-----------------|
| [path/URL/title] | [repo doc / prior spec / user doc / vendor doc / official doc / other] | [why it matters] | [what the spec must honor] | [aligned / conflict resolved / planned_stop / not relevant] |

**Ignored / Outdated Sources**: [List sources reviewed but rejected, with reason, or "None"]

**Open Documentation Conflicts**: [Any conflict that needs clarification before planning, or "None"]

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Boundary & Invariants *(mandatory for replacements, migrations, agents, or side-effecting systems)*

<!--
  ACTION REQUIRED: Fill this section when the feature changes an existing
  runtime, can trigger external side effects, uses agent tools, has multiple
  workers/runtimes, or depends on production state outside the repo. If none of
  those apply, mark this section N/A with one sentence explaining why.
-->

**Single Product Invariant**: [One sentence that must be true in production, or N/A]

**Forbidden Old Behavior / Side Effect**: [What must become impossible, or N/A]

**Legacy And Bypass Inventory**:

| Surface | Current / Old Behavior | New Allowed Behavior | Required Proof |
|---------|------------------------|----------------------|----------------|
| [tool/runtime/file/cron/job/API/UI/etc.] | [what can happen now] | [what may happen after this feature] | [negative test, visible proof, or read-only receipt] |

**Negative Acceptance Scenarios**:

1. **Given** [old/bypass path is attempted], **When** [natural request or runtime action happens], **Then** [the forbidden behavior cannot occur]
2. **Given** [missing guard/migration/env/service], **When** [readiness or workflow starts], **Then** [the system fails safe before side effects]

**Production Equivalence Need**: [N/A or the code/schema/env/service/cron/job proof required before live acceptance]

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]

## Implementation State Ledger *(maintained after implementation begins)*

<!--
  Leave this as Not started when creating the initial spec. During implementation
  and before closeout, update it whenever the accepted path differs from the
  official/production target, especially when a beta, staging, proxy, dry-run,
  or alternate transport path passes first. Evidence reports support this
  ledger; they do not replace it.
-->

**Closeout Status**: Not started

| Date | Current Implementation Pass | Official / Production Path State | Remaining Contract Gaps |
|------|-----------------------------|----------------------------------|-------------------------|
| [DATE] | Not started | Not evaluated | None yet |
