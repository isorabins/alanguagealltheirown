# US6 Offline Evidence — Moderated Suggestions

Result: **PASS for local contracts; deployed visible journey remains blocked**.

- The public form is directly below the live agent windows and clearly says submissions remain private until review.
- Text is length-bounded, stored literally, and idempotently queued; HTML, script, secret-like, URL, and prompt-injection strings receive no execution or special authority.
- Pending and dismissed rows are omitted from public state and cannot enter agent context.
- Approval changes only a matching pending id. At most one approved suggestion is delivered as an `optional_suggestion` object outside motion parsing.
- Delivery is exact-once; the following agent turn records `acted` or `no_action` from the independently enforced motion receipt.
