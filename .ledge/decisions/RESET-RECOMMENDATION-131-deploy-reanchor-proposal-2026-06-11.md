---
type: decision
subtype: reset-recommendation
status: accepted   # CO-SIGNED by the operator 2026-06-12 (stakeholder interview R1-Q1: "Post-wave anchor now") — the clock is RE-ANCHORED
title: "RESET-RECOMMENDED — the 15:24:21Z anchor was raced by the operator's own #131 CVE merge→deploy (:512); re-anchor proposed at 2026-06-11T19:25:44Z with the substrate rung CARRIED by quasi-src-identity"
date: 2026-06-11
detected_by: eunomia E4 post-merge PV-CLOCK discipline (the MF-1 window-integrity class, proven in anger ~2h after being specified)
evidence_grade: MODERATE (recommendation; the declaration is the operator's)
co_signed:
  anchor_utc: 2026-06-12T09:02:05Z   # :516 "reached a steady state" — the post-wave FINAL task-def (the :512→:516 chain is image-identical fa265ce, floor 2048/8192 held at every revision: :513/:514/:515/:516 verified)
  target_clear_utc: 2026-06-19T09:02:05Z   # +7 clean days
  substrate: ECS :516 / image fa265ce (warmer lockstep fa265ce; floor held)
  co_sign_receipt: stakeholder interview 2026-06-12, Round 1 Q1 — operator selected "Post-wave anchor now"; intent = the post-wave steady moment (per the 21:5xZ addendum), realized at :516 steady 09:02:05Z
---

# RESET RECOMMENDATION — the #131 deploy raced the clock; the cure rung carries

> **ADDENDUM 2026-06-11T21:5xZ (hygiene K0 PV gate):** before this proposal was co-signed, a
> **fleet-wide Satellite Receiver wave** (autom8y head `31e1e387`, runs 273794711xx, 21:46Z —
> ads/scheduling/data/sms/asana) rolled the asana service again: **`:513`** registered 21:48:03Z by
> `github-actions-deploy`, **same image `fa265ce`, floor 2048/8192 HELD** — a config-level reroll,
> behavior-neutral at the image altitude. asana main is UNMOVED (`fa265ce1`). The proposed anchor
> therefore moves once more: **re-anchor = the `:513` (or post-wave final task-def) steady-state
> moment**, clear = that moment +7d. The rung still CARRIES (image-identical). Co-sign remains the
> operator's; the sentinel's day-1 of the new window starts at whichever steady moment is co-signed.

## The event (receipts)
- PR **#131** `fix(deps): bump pyjwt to 2.13.0 for 4 CVEs` — authored + merged by the OPERATOR at
  **19:05:08Z** (a deliberate security action; 4 CVEs outrank a soak clock).
- → Satellite Dispatch → ECS **`:512`/`fa265ce`** created 19:16:03Z, **steady 19:25:44Z**
  ("deployment completed" + "reached a steady state" events); floor cpu=2048/mem=8192 preserved.
- The reset law (IC-SOAK-REANCHOR §RESETS): "a deploy mid-window (new task-def = new soak)" —
  the **15:24:21Z anchor on `:511` is VOID by the law's letter** (it lived 3h41m).

## Why the substrate rung CARRIES (no re-game-day demanded for the re-anchor)
Per the ratified STRONG spec's window-integrity clause ("any motion = operator-authorized +
src-identity-proven → the rung carries"):
- `git diff 49099b12..fa265ce1` = **`uv.lock` ONLY, 3 insertions / 3 deletions** (the pyjwt pin).
  src/ = 0, tests/ = 0, Dockerfile = 0, pyproject.toml = 0.
- **pyjwt is not imported by the soak-subject planes**: `git grep "import jwt|from jwt" fa265ce1 -- src/`
  = EMPTY (no first-party import anywhere in src/; the dependency serves library-level auth).
- The PRESERVE machinery, `write_final_artifacts_async`, `_memory_get_serviceable`, and the band
  code are **byte-identical** on `:512`. `self-heal-game-day-proven` + the E1 corroboration carry.
- Post-deploy health: band `unit 724/3027 · offer 1332/4079 · gun 8 · coherent 568` (all floors
  hold), `up==1` (ip-10-0-130-5), alarms 3× inactive-armed.
- The clear-day re-game-day (pre-written, CHAOS-DESIGN §4) remains the at-clear acceptance as
  already planned — unchanged.

## The proposal (operator co-sign = the declaration)
1. Declare the 15:24:21Z anchor VOID (lineage entry #5; the law applied to the operator's own
   deliberate motion — the discipline is symmetric).
2. **Re-anchor: 2026-06-11T19:25:44Z on `:512` → clear 2026-06-18T19:25:44Z.** The clock slides
   +4h04m; nothing else changes.
3. The sentinel ritual continues: the next daily record is **day-1 of the NEW window** (the prior
   day-1 attestation + its E1 corroboration remain valid evidence of plane health and method
   soundness — they re-base, they do not re-run).
4. The ratified STRONG spec stands as written (it is anchor-agnostic; its window-integrity clause
   is the very rule applied here).
5. DEFER unchanged; asana MERGE-FREEZE resumes from NOW until the new clear (PRs #130/#132/#114/#97
   stay held; the #131-class exception remains the operator's own lever, with this same
   re-anchor cost each time it fires).

## The meta-receipt (why this catch matters)
MF-1 (the deploy-freeze blindspot) was specified at E1 ~17:30Z; the window-integrity rider was
ratified ~19:30Z; **this event was caught by exactly that discipline ~19:40Z** — not by a daily
attestation (next due 06-12), but by the post-merge PV-CLOCK re-check. The sentinel method's
hardening proved itself in anger the same day it was written.
