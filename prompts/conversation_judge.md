Judge the complete six-message exchange against `numbered_requirements`.

Return exactly one JSON object with these top-level fields:

- `requirements`: one object for every numbered requirement, exactly once and in order. Each object MUST use the integer field `id` copied from `numbered_requirements` and the boolean field `pass`. It may also include a short `evidence` string.
- `concrete_outcome`: a short string describing the operational result.
- `contradictions`: an array of strings.
- `summary`: a short string.

The required row shape is `{"id": 1, "pass": true, "evidence": "..."}`. Do not rename these fields to `requirement` or `verdict`, do not use string verdicts, and do not decide the top-level `valid` field; the harness validator owns validity.

A pleasant conversation is not success: every required value, owner, constraint, and next step must be correct and unambiguous. Output JSON only.
