# Field note: plain-English control experiment

On 2026-08-01 WITA, the matched B1 plain-English control produced 29% message-body reduction and 87% semantic coverage: meaning FAIL, compression FAIL, zero inventions. The failed atoms were B1.16, B1.17, B1.19, and B1.31. The manager verified these structured facts with `jq` against the live-attempt `baselines/frozen-english-v2.json` before that product artifact was deleted as part of the scope reduction.

B2 was inconclusive. The preserved decoded sample used the correct phrase “five minutes”, but the literal validator accepted only singular variants. Both judge attempts were quarantined as `INVALID JUDGE RESULT: deterministic_conflict:B2.05`. The B2 invalid result and spend were verified from the ignored local receipt `baselines/frozen-english-progress.local.json`. The shared validator and benchmark were not changed.

Recorded post-repair cumulative provider spend was `$0.00534167912`. The earlier discarded pre-repair B1 attempt lacked an exact receipt. The conservative total-spend bound below `$0.03` used OpenRouter's public `/api/v1/models` catalog, queried on 2026-08-01 for `deepseek/deepseek-v3.2` and `moonshotai/kimi-k2.6`.

Iso explicitly reduced scope by removing the English control and control-adjusted projection. No claim is made that ALATO beats English compression.
