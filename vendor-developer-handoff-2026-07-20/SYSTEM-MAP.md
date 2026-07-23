# System Map

## Current Shape

```text
15-minute VPS timer
  -> run_turn.sh
  -> loop.py
       -> Agent A: DeepSeek legislature
       -> Agent B: DeepSeek legislature
       -> parser mutates state/rulebook.json
       -> blind payload + answer key
       -> DeepSeek encoder
       -> Kimi stranger decoder
       -> DeepSeek item judge
       -> state/conversation.json + state/meta.json
       -> viewer/state.js snapshot
  -> probe.py dumb-script measurement
  -> tweet.py Upload-Post delivery

Vercel static site
  -> viewer/index.html + viewer/state.js
  -> viewer/api/encode.js
  -> viewer/api/decode.js
  -> viewer/api/judge.js
  -> OpenRouter
```

The public site is not git-linked for deployment; the historical path is an explicit Vercel deploy from `viewer/`. A git push alone does not publish the site.

## Current Failure Boundary

```text
canonical rule ledger
  -> adopted + proposed text rendered together
  -> ordinary corpus exam
  -> one corpus score stamped onto many rules
```

That prevents rule-level attribution and makes labels such as “awaiting exam” or “survived N exams” unreliable.

## Target Shape

```text
canonical rule ledger
  |-> legislature view: adopted + proposed + rejected + history
  |-> language view: adopted only
  |-> explicit proposal trial: adopted + one labeled proposal

DeepSeek A inventor
  -> one focused proposal/revision/measurement
Kimi B auditor
  -> critique/adopt/reject/request focused test or revision
parser authority checks
  -> forbidden/no-op/repeated motions cannot mutate state

adopted language view
  |-> ordinary exam -> Kimi stranger -> exact-coverage judge
  |-> judged multi-turn Conversation
  |-> version-pinned public Try It

durable collaboration inbox
  |-> RESEARCH request/result with citations
  |-> ASK question + Iso answer from /human
  |-> visitor suggestion + Iso moderation
  -> loop consumes bounded events
  -> loop alone writes canonical experiment history

verified state
  -> selectively collapsed public page
  -> current README/MECHANICS
  -> confirmed/idempotent/bounded X delivery
```

## Role Separation

- Agent A: DeepSeek inventor; proposes or revises one idea, never votes.
- Agent B: Kimi auditor; evaluates A's latest idea, never starts an unrelated rule.
- Stranger decoder: separate stateless Kimi call; gets adopted rules plus encoded message only.
- Judge: validates every answer-key id exactly once before code computes fidelity.
- Human: controls the experiment, moderation, and live/public gates; does not write language rules.

## Deliberately Unchanged

- The 15-minute loop cadence.
- The existing last-ten passing-exam average.
- The 50% target and affordability/access purpose.
- Hypothetical cached economics for now, clearly labeled as hypothetical.
- Append-only historical evidence.

