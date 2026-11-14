---
type: decision
artifact_type: RULING
status: accepted
initiative: substrate-v2-epoch
wave: S8-2 (P5 live-parity window — EXTENSION)
date: 2026-08-11
author: OPERATOR (in-channel word, verbatim below) — inscribed by the main thread
ratification: OPERATOR-DIRECT (this resolves the extend-or-hold decision surfaced by HANDOFF-s8-parity-2026-08-11.md, PR #335)
consumes: .ledge/handoffs/HANDOFF-s8-parity-2026-08-11.md
---

# OPERATOR RULING — S8-2 window EXTENDED

**Operator (verbatim, 2026-08-11 ~10:36Z):** "I marked task 2 complete, extend"

## Effect (per the surfacing packet's recommended terms)

1. **EXTEND** is the word of record; HOLD is off the table. The original 7-day ceiling
   (2026-08-12T09:19:45Z) is superseded.
2. **New bound: fresh 7-day HARD ceiling from the word — 2026-08-18T10:36:46Z.**
   Floor unchanged: ~3 days of cadence diversity. Per rubric §2(d), the restarted parity
   count begins at the FIRST post-restart warm cycle observed in parity. Day-1's banked
   evidence (RC-F-2, C10 fires+quiet, the drift verdict, the composition catalog) carries;
   the ≥2-warm-cycle count restarts at zero.
3. **Data precondition discharged in the same word:** the operator marked
   `1216414611774709` complete → the AUTOM8 Business-Offers trigger provisions its
   Offer ID (the identical mechanism observed on `1213234683414144`: completion 5:26pm →
   Offer ID "1606" set 5:27pm, 2026-08-10 — activity-log evidence on record). The next
   v1 warm (~30-min cadence) carries it into the frame; the restart sweep's floor verifies
   rather than assumes.
4. **T2 restored before the word:** active rite re-synced to 10x-dev
   (`ari rite current` 2026-08-11: Active Rite 10x-dev; sre co-seated additively,
   inv-20260811-7dc640ec7e0d). Corridor execution is lawful again.
5. **PROV state at EXTEND (own-hands describe-alarms, 2026-08-11 ~10:33Z):** PROV-2 ALARM
   since 2026-08-05T17:22Z — the dead-man truthfully alarming through six sweep-less days;
   clears at the restart sweep's heartbeat. PROV-1/PROV-4 read OK via
   missing-data→notBreaching (honest silence while nothing sweeps — NOT proven-clean;
   they re-assert on the next emission). PROV-3/5/6 OK. No anomaly blocks restart.
6. **Freshness-integrity note banked:** the suspected "deeper lie" was affirmatively
   FALSIFIED by the task-1 activity log — null was true at every 08-05 capture; the field
   was provisioned 08-10T17:27Z by the completion trigger; today's 09:15Z frame carries it
   within SLA. Full lifecycle (absent → provisioned → extracted) observed truthfully across
   three independent capture points. Side-finding routed to the intake/provisioning
   workstream: `Error Refreshing LeadTestingLink: 'Dna' object has no attribute 'is_active'`
   (live AttributeError leaking into task comments, 2×, 2026-08-10T17:27Z).

## Restart sequence (armed)

Runner re-authored from the records (QA receipt LIVE INVOCATION RUNBOOK + the merged cures
#313/#318 + the five-invariant composition catalog in HANDOFF-s8-parity-2026-08-11) →
offline validation → first restart sweep (fresh creds, off-peak, full-stream capture) →
observation #1 → standing pythia seat classifies → daily digests per G5 resume.
