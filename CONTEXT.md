# A Language All Their Own

The shared language for the public experiment in which two legislators evolve
and test a compact agent-to-agent language.

## Language

**Adopted language**:
The current rule text allowed to govern encoding and decoding, identified by a
deterministic version and hash.
_Avoid_: Rulebook, when rejected or historical records are also meant

**Complete legislature**:
The full record of adopted, proposed, rejected, repealed, and historical rules.
_Avoid_: Adopted language

**Open motion**:
The single unresolved proposal or repeal that constrains the next legislative
action.
_Avoid_: Active rule

**Active legislative feedback**:
Agent B's exact unresolved request about the current open motion, retained until
it is superseded or the motion settles.
_Avoid_: Recent context, conversation memory

**Development exam**:
One run of a frozen B1-B5 message used repeatedly to improve and regression-test
the adopted language.
_Avoid_: Holdout, transfer test

**Transfer evidence**:
Evidence from material outside the repeating development exams, used to judge
generalization rather than train the legislators on a familiar fixture.
_Avoid_: Development exam

**Frozen English baseline**:
The versioned one-time ordinary-English control result paired with one corrected
development exam under matching models, tokenizer, instructions, and budget.
_Avoid_: Scheduled control test

**Unseen comparison**:
A manual, operator-held paired evaluation on three new messages, used only
before a major generalization claim.
_Avoid_: Development benchmark, recurring test

**Message-body savings**:
The token reduction from an original message to its encoded body, excluding the
rulebook and other request context.
_Avoid_: Total cost savings, API-bill savings

**Projected conversation-cost savings**:
A labeled hypothetical comparing a fixed multi-exchange plain-English scenario
with rulebook-assisted communication, including the stated rulebook-cache cost.
_Avoid_: Actual savings, provider telemetry

**Control-adjusted projected savings**:
The difference between ALATO's projected conversation-cost savings and the
matching frozen English baseline's projection.
_Avoid_: ALATO savings, when no English control is shown
