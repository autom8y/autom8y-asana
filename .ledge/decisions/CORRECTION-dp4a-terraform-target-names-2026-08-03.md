---
type: decision
artifact_type: CORRECTION
status: accepted
corrects: .ledge/decisions/DP-4a-READY-provability-alarms-apply-2026-07-30.md (§ "exact lever" command block ONLY)
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-03
session: session-20260803-220334-f2a75514
main_sha: 5d62d0b8e8ec18b82e9325ddc249c7a4c4296baf
author: main thread per potnia wave-ENTRY ruling G4(i) (RULING-potnia-s8-2-wave-entry-2026-08-03.md)
ratification: P13 [A-2026-08-03] staged-auto — inscribed 2026-08-03T16:50:01Z
discovered_by: SVR vetting agent (sonnet Explore fanout, S8-2 preflight), finding #23
---

> Provenance (P13 [A-2026-08-03]): auto-ratified STAGED on inscription;
> 24h operator amend window opens 2026-08-03T16:50:01Z; one word reverts.

# CORRECTION — DP-4a "exact lever" terraform `-target=` resource names

## The defect

DP-4a-READY's operator-facing "exact lever" command block cites four terraform
`-target=` resource addresses that DO NOT EXIST in
`terraform/services/asana/substrate_v2_provability_alarms.tf`. Literal execution
of the documented block would fail with "Resource … not found" on 4 of 6 targets.
The same record's own §Ratification section uses the CORRECT names — an internal
self-contradiction within DP-4a, not merely stale docs.

## The correction (names of record)

| DP-4a "exact lever" (WRONG) | Actual tf resource (CORRECT) | tf line |
|---|---|---|
| `prov2_heartbeat_deadman` | `aws_cloudwatch_metric_alarm.prov2_heartbeat_absence` | :142 |
| `prov3_staleness` | `aws_cloudwatch_metric_alarm.prov3_incomplete` | :170 |
| `prov4_coverage` | `aws_cloudwatch_metric_alarm.prov4_expected_set_mismatch` | :199 |
| `prov5_refusal` | `aws_cloudwatch_metric_alarm.prov5_expected_floor` | :230 |

Unaffected (already correct in DP-4a): `prov1_unprovable` (:113),
`prov6_future_dated_proof` (:260).

## Scope + non-impact

- The DP-4a RULING itself (`applied`, 2026-07-30) is UNAFFECTED: the local
  `terraform.tfstate` (serial 7, mtime 2026-07-30 13:56:10 UTC) contains exactly
  the six CORRECTLY-named resources, and all six alarms are live in CloudWatch
  (own-hands describe-alarms sweep, 2026-08-03: PROV-2 ALARM-as-predicted,
  PROV-1/3/4/5/6 OK).
- This correction pins the reproducible lever for: state-file loss recovery,
  future re-applies, and the fleet-template mission goal (a wrong lever poisons
  the "template application, not a research project" bar).
- Any future consumer of DP-4a MUST read this correction alongside it; the
  "exact lever" block in the original is superseded by the table above.
