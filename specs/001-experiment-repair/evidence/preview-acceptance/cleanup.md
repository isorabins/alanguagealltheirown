# Preview and lease cleanup receipt

Date: 2026-07-23 WITA

- Final Preview cleanup endpoint returned HTTP 200 after removing 12 keys in
  namespace `alato:v1:*`; `remainingKeys` is `0`.
- Final lease `cbx_de7cea9d8ff0` (`violet-lobster`, Hetzner server
  `154399309`) was released after evidence collection.
- Fresh coordinator query: zero active leases.
- Fresh Hetzner readback: released server ID returns HTTP 404; isolated project
  contains zero SSH keys.
- Coordinator monthly usage after release: 3,909 runtime seconds and `$0.07`
  cumulative estimated infrastructure spend. The final lease stayed within its
  separately approved `$1` ceiling.

The final recording completed naturally at 180.000 seconds. Cleanup and the
overall Preview evidence audit are `PASS`; Production is unchanged.
