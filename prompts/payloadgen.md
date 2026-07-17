You write one realistic message that one working AI agent sends another mid-task. It will be
used as a test payload: another system must carry it faithfully, so it should be the kind of
message where every detail matters.

Category: {CATEGORY}

- prose: an explanation, update, apology, or note the receiver needs relayed
- task: a work request or instructions — steps, constraints, priorities, a judgment call
- data: a message whose center of gravity is data (figures, IDs, times, configs) with the
  sender's intent attached

Domain for this one: {DOMAIN}

Requirements:

- 400–600 words, plain text, written as a direct message from one agent to another
- Concrete specifics: at least three names or identifiers, at least six quantities or times,
  and at least three conditionals ("if X, do Y") or scoped instructions ("only the X, not the Y")
- Fresh invented subject matter — no famous names, no placeholder text, no lists or headers
- After the message, output a line containing exactly ===KEY=== followed by the answer key:
  a numbered list of every piece of information the message must carry to count as faithfully
  relayed — each quantity with its unit and what it refers to, each identifier and name, each
  instruction with its condition and scope, each time or deadline, each required ordering of
  steps. 10–20 items, one per line, each a short self-contained statement. The key describes
  only what the message actually says.
- Output ONLY the message text, then ===KEY===, then the key — nothing else
