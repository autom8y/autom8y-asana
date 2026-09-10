# HANDOFF — name-the-client · WAVE 1 · THE ENFORCEMENT GAP · overnight seam

**Authored:** 2026-09-10 ~04:40Z · seat `calendar-integration-locus` (d5861864) · rite `sre`
**Charge:** `.sos/wip/CHARGE-name-the-client-wave1-2026-09-10.md` · **Governing sitting:** `.ledge/decisions/RATIFICATION-decision-space-sitting-VII-2026-09-10.md` (R-112 … R-122) — **landed to asana main in the same PR as this handoff; until then it existed in one working tree only (the attester flagged this).**
**Bar graded against:** `.know/telos/name-the-client.md` @ asana `83a9ae99` — **AMENDED tonight** (R-113): (c) split into (c1)=1 office both poles / (c2) BOOKED OPEN.
**`ari knows --validate`:** 1,700 broken references. **Every `@` reference below is unvalidated by default.** Verify at the stated ref, never from memory.
**Self-cap:** MODERATE. Two receipts are PENDING at authoring time and are marked `[PENDING …]`; a later seat patches them in place — it does not assume them.

---

## §0 THE THREE SENTENCES

1. **Clauses (a), (b), (c1) are ATTESTED by a rite-disjoint seat at the amended bar** — (b) with a flag — and **three offices carry both poles.** **Wave 1 is NOT CLOSED:** (d) is unbuilt. ★ **Scoping correction, caught by the attester:** this seat's dispatch cited R-121 as the authority for grading three legs; R-121 governs work threads. **R-116 says build (d) first, then verify all four.** The anchors for "(d) unbuilt tonight" are **R-119 and sitting VII §5**, and the three-leg verdict is worded so it cannot be read as operator-sanctioned closure. Right object, wrong question — aimed at the attestation, caught by it.
2. **Three production-adjacent changes landed tonight under the sitting-VII grant, each with a two-sided receipt:** V13 recorded (`autom8y` `47f50912`, byte-identical to this seat's superseded #2135), the telos amended (`asana` `83a9ae99`), and the scheduling refusal discriminator (`autom8y-scheduling` `da24ab49`, deploy in flight `[PENDING AFTER]`). **The deploy hazard (#2120) was already merged** and is now measured at 641 → 201 prose files with a justified residual.
3. **The organizing defect — a declared instrument with no enforcement on what it protects — was found in THREE new places tonight** (carriers #7, #8-revised, #9), and the S1 census found **zero of 9 named instruments carry an occurrence floor while 37 floor-shaped alarms already exist fleet-wide.** The primitive exists; it is unextended.

---

## §1 DAG STATE — PER NODE

`SVR` = seat-verified receipt on the record · `UV-P` = unverified, method deferred · `RULED` = operator word on the record · `REFUSED-CORRECTLY` = a node that was right not to execute (distinct from a failure)

### LIMB C — CONTAINMENT (`autom8y`)
| N | state | receipt |
|---|---|---|
| **C1** | **SVR** | `.sos/wip/C1-orphan-module-adjudication-2026-09-10.md` (529L) + `.sos/wip/C1-corroboration-main-thread-2026-09-10.md` (74L, independent). All three orphans **UNRECORDED, none DEAD**: `asana-redis`→`asana`; `recon-canary-synthetic-upstream`→`account-status-recon`; `serving-color-alarm`→7 services / 8 blocks. **Escalation confirmed own-hands:** `manifest-query.sh module-consumers` feeds `service-terraform.yml:194`; an unrecorded module → `[]` → zero stacks planned. |
| **C2** | **RULED R-112** → executed | Landed as `47f50912` by another seat, **byte-identical** (37,744 B, `diff rc=0`) to this seat's #2135 (closed superseded). V13 **PASS 20/20** on main; `module-consumers serving-color-alarm` → `["auth","api-gateway","ads","data","asana","scheduling","sms"]`, was `[]`. |
| **C3** | **DONE** | #2120 merged 01:32:12Z. **Verified on main, not PR state:** negated `paths` (`!services/**/.ledge/**`, `.know`, `.sos`, `tests`). **641 → 201 `.md` in radius.** Residual is deliberate: **13 of 15 Dockerfiles COPY a README** (reproduced own-hands). |
| **C4** | **NOT STARTED** | Negative half (docs-only `services/**` commit → 0 dispatch runs) not run tonight. Positive half `[UV-P: fence positive pole \| METHOD: organic next-apply observation \| REASON: synthetic positive control IS the hazard]`. **NO WATCHER.** |
| **C5** | **SVR** | `validate-manifest.sh` against main's manifest: `[FAIL] V13 19/20 rc=1` → `[PASS] 20/20 rc=0`; positive control (mutated copy fails a different check) not separately run — **inherited from C1's V13 replay, which reproduced exactly three rows and self-corrected from seven.** |
| **C6** | **OPEN — OPERATOR** | `push: branches:[main]` on `manifest-validate.yml` not added. **Now SAFE to arm** (V13 green on main, so it would not be red-on-arrival — R-109's objection no longer applies). One word. **NO WATCHER.** |

### LIMB B — CLAUSE (b) (`autom8y`)
| N | state | receipt |
|---|---|---|
| **B1** | **SVR, with two corrections** | `.sos/wip/B1-clause-b-carrier-measurement-2026-09-10.md` (588L). Named carrier **`booking_gate_declined`**: 2,303/90d, 282/7d, 100% post-attempt, 100% office-knowable, in-alternation control. **Correction 1:** its "one-call-site field add" was read off the STALE checkout — the add is already on main (#2125). **Correction 2 (by S1):** its `booking_wrote_nowhere` recall-decay finding is **FALSIFIED** — wrong denominator; see carrier #8. |
| **B2** | **SVR** | `.sos/wip/B2-office-name-provenance-2026-09-10.md`. `office_name` = `full_business.business_name` off `get_business_by_phone_async` at `:290`; **resolved against a record we hold, NOT envelope-echoed.** `resolve_source` governs the GUID only. Pythia's self-named largest hole closes in its favour. **F-β antecedent falsified**; residual (6 `raise` sites above the lookup) is already kind `absent`, never blank. |
| **B3** | **REFUSED-CORRECTLY** | `.sos/wip/B3-COLLAPSED-clause-b-already-live-2026-09-10.md`. Nothing to build — #2125 already carries `**office_log_fields(ctx)` at `book_appointment.py:183`. B1 delivered the missing **(ii) SUBJECT LIVE** half for an instrument that already had (i). |
| **B4** | **MOOTED** | #2125 merged 23:56:12Z by `name-the-wave` on its own operator's word in its own room. Not on a relay. |
| **B5** | **SVR** | Live failure lines, named: `booking_gate_declined` × 4 offices after 00:13Z (`c2ab6637` Axis Spine, `8e56f6e1` Optimal Health ×2, `87bd31d7` Network Wellness), **17 blank before 00:06Z — clean deploy-boundary cutover, no interleaving.** Plus `terminal_decline` named on `087d7de5`. |
| **B6** | **OPEN** | #2071 reassess (R-104 step 3). **NOT DONE. NO HOLDER. NO WATCHER.** |

### LIMB A — AD-LEAD
| N | state | receipt |
|---|---|---|
| **A1** | **DISCHARGED-BY-MECHANISM** (not by sampling) | Peer `name-the-wave` Addendum 59 + this seat's own-hands code read: `_refuse_ad_lead_gate` returns COMPLETED, must not raise/FAIL, runs BEFORE `record_intent`; `book_appointment.py` is a separate stage. **Structurally cannot block a booking.** Refusal limb **nominal**: ~50/day vs SPEC §12 `~53/day mean, 244/day max`. **This seat over-alarmed on "90.7%" earlier; withdrawn.** |
| **A2** | **OPEN** | Deviation alarm `ad_lead_gate_refusal_dominant` ≥50/15min vs ~0.5/15min live — **0 of 769 buckets ≥ 50, max 9.0** (S1). Author dated replacement "~2 weeks post-gate" ≈ **2026-09-15**. **NO WATCHER.** |

### LIMB S / R
| N | state | receipt |
|---|---|---|
| **S1** | **SVR** | `.sos/wip/S1-instrument-census-2026-09-10.md` (613L). **0 of 9 named instruments / 58 filters carry a floor. 37 floor-shaped alarms fleet-wide, 1 of 26 in EBI.** Four wrong-object failures inside the census, all caught by controls (worst: `--limit 1000` → exactly 1000 rows → recall 1.0000). |
| **S2** | **SURFACED ONLY** (RATIF-VI-D8) | Not pre-committed. The successor shape: extend the existing floor-alarm template, exempt self-failure detectors where zero is healthy (S1 §6.2). |
| **R1** | **THIS ARTIFACT** | + corrections §4. |
| **R2** | **DONE** | `asana` `83a9ae99` (#427). Verified on main: (c1)/(c2) present, retired phrasing absent, **zero raw client names**, redaction tokens intact. |
| **R3** | **ATTESTED (a) · ATTESTED-WITH-FLAG (b) · ATTESTED (c1) · (d) UNBUILT** | `.ledge/reviews/ATTEST-name-the-client-wave1-legs-abc1-2026-09-10.md` (528L, eunomia, rite-disjoint, inherited nothing). **Wave 1 NOT CLOSED.** Three offices carry both poles. #2105 fails SUBJECT-LIVE in one query (0 / 0 vs controls 6,527 / 2,306 / 1,437). 28,091 pre-deploy failure lines zero-named → 100% named after, hourly-binned with in-query control. **Flags:** F-3 `booking_gate_declined` has **NO DIRECT PROBE** (only in a docstring; pre-existing test stays GREEN if that site is reverted) · F-4 `ad_lead_gate_refused` (7) + `booking_intake_fault` (15) still ALL BLANK · F-7 7d count of record is **269**, not 282. **(a) was cured by #2073 `571e80d8`, not #2125** — corrected here. |

### NEW TONIGHT — outside the charged DAG, inside the sitting-VII grant
| item | state | receipt |
|---|---|---|
| **SCHED-1 discriminator** | **MERGED `da24ab49` @ 04:26:41Z · `[PENDING AFTER]`** | `autom8y-scheduling` #75. Additive: `offer_resolved` / `offer_guid` / `offer_disabled` on `scheduling_gate_rejected`. **Two-sided:** cure 70 passed · mutant 4 FAILED + positive control PASSED · restored 70 passed. **BEFORE (live, `/ecs/autom8y-scheduling-service`, 58 scanned):** `extra` keys `[office_phone, reason]`, `offer_resolved` ABSENT ×5. AFTER: deploy chain Test → satellite-dispatch → ECS in flight at authoring. |
| **SCHED-2 NULL-shadow** | **CHARACTERIZED; fix NOT AUTHORED** | `.sos/wip/SPLIT-not-enrolled-and-null-shadow-2026-09-10.md` (388L). Path **reachable**; **0 live instances** (taken zero, both controls fire); **177 offices ARMED** one enabled-row insert from firing; NULL class fastest-growing (326→386). **This seat said it would author a proving test and park a fix; it did not get to it.** Sitting VII §3.1 holds: behaviour change stays parked for a dawn word regardless. |
| **F-2 decision page** | **SVR, awaiting OPERATOR** | `.sos/wip/F2-activating-vocabularies-2026-09-10.md` (368L). **9 named sites across 5 grains** (commit said 4+/3). Disagreeing pair proven by execution: `UNIT_CLASSIFIER` vs `_VENDORED_MONOLITH_SECTIONS`, project `1201081073731555`, Engaged/Scheduled → `activating` vs `inactive`. **"Use both" is not an option** — `guard()` refuses multi-grain. **`taxonomy_divergence` will not catch it.** No recommendation. |
| **Clause (d)** | **NOT BUILT — blocked on F-2** | Foundation `b17a066c` (asana, **BRANCH-ONLY**, not on main) ships no default referent by design. Every disputed vocabulary is on main; the branch adds only the mechanism that refuses to choose. |

---

## §2 RISK MAP

| # | carrier | status tonight |
|---|---|---|
| 1 | `manifest-validate.yml` no `push:` — main never validated | **Still open.** Now safe to arm (C6). Operator word. |
| 2 | docs commit → whole-stack `terraform apply -auto-approve` | **Reduced 641 → 201**, residual justified. Still `-auto-approve`, still no `-target`. |
| 3 | ad-lead deviation alarm ~100x unreachable, replacement due ~09-15 | **Open. NO WATCHER.** |
| 4 | 15 divergences reaped by TTL before naming | **Open. NO WATCHER.** Reconstruction path via `office_resolved` (guid+name, 100% coverage) untried. |
| 5 | #2105 cure on a dead path | **Superseded** by #2125 on a live path; #2105 stays on main, harmless, with a permanent `[DO NOT MERGE]` subject (§4). |
| 6 | freeze gate inert during its own window (R-109) | **Changed shape:** #2119 made it declaration-driven; no declaration on main; gate passes. R-109's concern now attaches to C6 instead. |
| **7 · NEW** | `module-consumers` call site `2>/dev/null \|\| echo "[]"` — **a broken query and an absent consumer are the same output**, in the deploy-planning path | **Mitigated** (modules recorded), **not cured** (the masking construct remains). |
| **8 · REVISED** | `booking_wrote_nowhere` — **NOT instrument decay** (B1's claim falsified). The **SUBJECT collapsed 21.5/day → 0.64/day (97%)** against its own declared "~25/day"; only alarm is increase-only at 60/day and **will never fire.** Cure or silent loss: **UNDETERMINED.** | **Open. NO WATCHER.** |
| **9 · NEW** | `scheduling_gate_rejected reason` — one string, four facts; **1,304/1,304 identical over 30d**; discriminator computed then discarded | **Cured in code** (`da24ab49`), **live receipt pending.** 96.1% of 2,305 refusals are the NULL case across 26 clinics; **rank-2 clinic (448 declines) was never named** — names exist on 5 of 2,305 records. |
| **10 · NEW · SECURITY** | Split agent reports production DB **`nhc-db` is publicly accessible** (it reached it read-only from a laptop) | **Flagged, not acted on.** Operator. |
| R-80 | ROLL-FORWARD-ONLY, NO RESTORE | Standing. Honoured. |
| R-109 | live instance | See #6. |

---

## §3 DEFER REGISTRY — namespace-qualified · `NO WATCHER` written where true

| id | item | waits on | watcher |
|---|---|---|---|
| **RATIF-VII-F2** | which `activating` vocabulary governs | **operator, at dawn**, from the F-2 decision page | **operator** |
| **RATIF-VII-(d)** | clause (d) build | F-2 | this seat, after the ruling |
| **RATIF-VII-NULL** | NULL-shadow proving test + parked fix | dawn word (sitting VII §3.1) | this seat — **not started** |
| **RATIF-VII-AFTER** | live AFTER receipt for `da24ab49` | deploy chain | this seat (bg watch `bvnebagsz`) |
| **RATIF-VII-R3** | attestation verdict | eunomia | this seat |
| **SHAPE-C4** | deploy-fence positive pole | organic next `services/**` apply | **NO WATCHER** |
| **SHAPE-C6** | arm `push:` on manifest-validate | operator | **NO WATCHER** |
| **SHAPE-B6** | #2071 reassess | — | **NO WATCHER · NO HOLDER** |
| **SHAPE-A2** | ad-lead alarm re-derive + the ~09-15 clock | — | **NO WATCHER** |
| **RATIF-I-(c2)** | coverage over a ruled population | WS-JOIN + identity ruling (R-110 one-page sitting) | **NO WATCHER** |
| **RATIF-VI-D8** | the successor epoch | "decide then" — surfaced by S1/S2 | operator |
| **CARRIER-4** | the 15 reaped divergences | a read via `office_resolved` nobody has run | **NO WATCHER** |
| **CARRIER-8** | `wrote_nowhere` subject collapse: cure or loss? | — | **NO WATCHER** |
| **CARRIER-10** | `nhc-db` public exposure | operator | **NO WATCHER** |
| **ATTEST-F3** | a DIRECT probe for `booking_gate_declined` — a test that goes RED if `office_log_fields(ctx)` is removed from `book_appointment.py:183` alone | test-only PR in `services/email-booking-intake/**` (within R-120) | **this seat, next session** |
| **SPLIT-rank2** | the 448-decline clinic never named | a name from `office_resolved` by trace join (split agent recovered all 29 phones) | **NO WATCHER** |
| **SHAPE-Dn vs RATIF-VI-Dn** | the D-numbering homonym | — | resolved by qualification in every artifact tonight; **carry the rule, not a watcher** |

---

## §4 CORRECTIONS TO THE RECORD

1. **#2105's commit subject on `autom8y` main reads `[DO NOT MERGE — R-35 PARKED]` permanently.** The merge was lawful (R-99). The prose asserts a falsehood about itself and cannot be rewritten. **Addendum, not amendment.** #2125 was retitled before merge on this finding.
2. **This seat's errors tonight, all caught:** live-image attribution stale by 27 min (substance survived) · over-alarmed on ad-lead 90.7% (withdrawn) · told the peer "five not six" conflating dark-office class with client count (withdrawn) · **"the telos has never been committed" — FALSE**, stale-branch read · **nearly re-committed raw client office names** from a stale unredacted working copy (caught by diffing base against main; discarded; redone). Fourth instance of the stale-referent class in one seat.
3. **B1 read the stale checkout twice**: reported `ad_lead_gate` "absent from the repo" (present on main, 5 files) and recommended a field-add already merged. **The stale-tree fence was named in the charge and landed on the third seat anyway.**
4. **Three blind test captures measured while landing `da24ab49`** — `capture_logs` (chain cached), `capsys` (sink bound to the stream object at import), `capfd` (autouse `log_reset_state` tears the sink down). Each yields the same output as a real defect. **Fleet `MockLogger` on the module logger is the sanctioned capture.** Recorded in the test docstring so nobody re-walks it.
5. **The recommendation-selection pattern:** sitting VII round 1 = 4/4, round 2 = **2/4 displaced**, round 3 = 2/4 displaced. Logged as a caution in the sitting; the breaks are the evidence the framing was not simply leading.

---

## §5 STANDING FENCES — UNCHANGED
Never-grantable floor untouched · freeze gate / ruleset 17263542 untouched either direction · nothing merged on a relay · nothing bundled · nothing merged past red · R-80 roll-forward-only · **no seat declares a clause closed — R3 attests.**

---

## §6 THE NEXT COMMAND LINE — cold-resumable

```bash
# 0. orient (this file), then re-resolve every ref by hand — the .know domains are STALE
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana && cat .ledge/handoffs/HANDOFF-name-the-client-wave1-overnight-2026-09-10.md
# 1. patch the two PENDING receipts if the bg watch / attester landed while you were away
cat /private/tmp/claude-501/-Users-tomtenuta-Code-a8-a8-repos-autom8y-asana/7f8de4af-738e-429d-9039-56ca238249ee/tasks/bvnebagsz.output | tail -8
ls -la .ledge/reviews/ATTEST-name-the-client-wave1-legs-abc1-2026-09-10.md
# 2. OPERATOR: rule F-2 from the decision page — nothing on clause (d) moves until this is a word on the record
${EDITOR:-less} .sos/wip/F2-activating-vocabularies-2026-09-10.md
# 3. OPERATOR, one word each: C6 (arm push: on manifest-validate — now safe), the NULL-shadow parked fix, nhc-db exposure
# 4. verify the AFTER state yourself before believing §1 SCHED-1:
aws logs start-query --log-group-name /ecs/autom8y-scheduling-service --start-time $(($(date -u +%s)-3600)) --end-time $(date -u +%s) --query-string 'fields @timestamp,@message | filter @message like /scheduling_gate_rejected/ | sort @timestamp desc | limit 5'
```
