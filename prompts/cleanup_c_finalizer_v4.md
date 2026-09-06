## Final editorial decision

Agent B supplied one advisory review of the previous candidate. You remain the
final decision-maker. Verify each finding against the frozen original.

The caller supplies `previous_draft`, the valid C-authored object that produced
B's reviewed candidate. Use that exact output structure as your starting point;
`previous_candidate` is its compiled representation for comparison. Preserve
unchanged assignments and exclusion markers verbatim. Any excluded source must
still map to the exact string `__exclude__` and have one matching exclusion entry.

Return one complete final edition. Correct genuine omissions or meaning changes
with the smallest possible edit; otherwise preserve the candidate. Keep the
strict schema, the total maximum of 16 legislative-memory entries, and the
23,000-character target for `groups` plus `legislative_memory`. The caller
rejects rather than truncates an oversized result.

No later model approves this edition. Deterministic code enforces coverage,
schema validity, the 25,000-character snapshot cap, token reduction, spend, and
source integrity. Return only the supplied schema.
