# Issue tracker: GitHub

Issues for this repository live in GitHub Issues. Use `gh` from this clone so
the remote determines the repository.

## Basic operations

- Create, read, comment, label, assign, and close issues with `gh issue`.
- Refer to issues by their linked title in human-facing Wayfinder material, not
  by a bare number.
- Pull requests are not a request or triage surface.

## Wayfinding operations

- A map is one issue labelled `wayfinder:map`.
- Each decision ticket is a GitHub sub-issue of the map and has exactly one of
  `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or
  `wayfinder:task`.
- Use GitHub's native sub-issue and issue-dependency relationships. If either is
  unavailable, use a task list on the map and a `Blocked by:` line on the child.
- Claim a frontier ticket before work by assigning it to the driving developer.
- Resolve a ticket with a resolution comment, close it, then add one linked gist
  to the map's `Decisions so far` section.
- The frontier is the map's open, unassigned children with no open blockers.

## Evidence rule

Every ALATO roadmap ticket must point to the mission brief under
`docs/wayfinder/` plus the narrow source files or commits relevant to its
question. Chat memory is not evidence.
