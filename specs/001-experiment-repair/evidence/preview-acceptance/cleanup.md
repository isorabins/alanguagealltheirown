# Preview and lease cleanup receipt

Date: 2026-07-22 WITA

- Preview cleanup endpoint removed 13 keys in namespace `alato:v1:*` and
  returned `remainingKeys: 0`.
- Lease `cbx_f1b87a5270c3` (`pearl-barnacle`) and follow-up lease
  `cbx_a0e11b226c2f` (`brisk-prawn`) were released after their permitted
  attempts.
- Fresh coordinator query: zero active leases.
- Fresh isolated Hetzner-project query: zero servers and zero SSH keys.
- Coordinator monthly usage after release: 3,366 runtime seconds and `$0.06`
  estimated infrastructure spend; the follow-up lease added about `$0.01`,
  within its separately approved `$1` ceiling.

The follow-up recording completed naturally as a 180-second MP4. Cleanup is
successful, but the overall evidence audit remains `FAIL` because row 9 failed
and rows 10–12 did not run.
