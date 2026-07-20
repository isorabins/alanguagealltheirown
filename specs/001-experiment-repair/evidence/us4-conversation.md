# US4 Offline Evidence — Judged Conversation

Result: **PASS (deterministic fixture); real-model artifact remains production-gated**.

- `test_conversation_exam.py` captures one adopted-language version/hash, gives both speakers only that language and a real-work scenario, and preserves exactly six messages in A/B/A/B/A/B order.
- A separate judgment object is tied to explicit scenario requirements.
- The rulebook remains deep-equal before and after the exam; ordinary exam counters/averages are not mutated by `run_conversation`.
- Scheduling is once per 32 completed ordinary exams and deduplicates by `ordinary_exam_count` after restart.
- No standalone overlapping one-message exam path was added.
