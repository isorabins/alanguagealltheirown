# Preview and lease cleanup receipt

Date: 2026-07-22 WITA

- Preview cleanup endpoint removed 13 keys in namespace `alato:v1:*` and
  returned `remainingKeys: 0`.
- Lease `cbx_f1b87a5270c3` (`pearl-barnacle`) was released after the final
  permitted attempt.
- Fresh coordinator query: zero active leases.
- Fresh isolated Hetzner-project query: zero servers and zero SSH keys.
- Coordinator monthly usage after release: 2,786 runtime seconds and `$0.05`
  estimated infrastructure spend; this is below the `$1` approved ceiling.

The required outer MP4 was not created when the recording process was stopped;
therefore this cleanup is successful but the overall evidence audit remains
`FAIL`.
