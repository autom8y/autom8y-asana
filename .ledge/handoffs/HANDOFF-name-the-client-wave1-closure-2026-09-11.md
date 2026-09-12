---
type: handoff
initiative: name-the-client → read-the-name
status: WAVE 1 CLOSED-WITH-REFUSAL (2026-09-11, R-147, attested rite-disjoint in ATTEST-name-the-client-wave1-closure-2026-09-11 / asana #442)
created: 2026-09-11
seat: calendar-integration-locus
---

# HANDOFF — name-the-client wave 1 CLOSURE · the READ epoch opens

**Line one:** wave 1 is **CLOSED-WITH-REFUSAL**. (a), (b), (c1) ATTESTED on fresh live receipts (F-3 DISCHARGED); **(c2) is OPEN**, carried into `read-the-name` as R3; **(d) is PROBE LIVE / SUBJECT DARK**, REFUSED-CORRECTLY and concurred by the attester: there is no activation path in production to gate.

## §0 THE THREE SENTENCES

1. **The plane names the client; nothing reads the name.** 38 of 38 bookings on 09-11 resolved to an office, 202 of 202 failure lines carry a kind, 15 offices carry both poles in one day. The 406-mail / 2-booking office is a **live, served-set client** at the Offer grain (one offer ACTIVE). The north's verb is now READ (R-135).
2. **Clause (d) closed on a refusal, not a build.** The lifecycle engine has no production entry point (no live constructor; no-op webhook route; no scheduler; 0 lifecycle events over 7.28M scanned records vs 17,773 on the control shape). The smoke module (#439, 43 tests) and the ruled Offer-grain referent (#441, 32 tests, G6-equivalent to `max_offer_activity`) are PROBE-LIVE artifacts awaiting the operator's merge word; the gate migrates to the READ epoch on a scheduled-sweep substrate — and the attester found that substrate may already be deployed as `/aws/lambda/autom8-asana-unit-reconciliation` (keys `ACTIVATING`, hard-coded `dry_run=True`, zero events across 553 boots). Unadjudicated; first spike of the epoch.
3. **No EBI code merged today, by ruling.** The HealthCom window (autom8y #2170) is on main; name-the-wave's dispatch failed twice on their own tfvars-comment guards (#2176 → #2179 pending); the third fire LANDED: alias `live` v66 → v67 at 21:18:21Z, the retain window SERVED (seat's qualified read: v67 modified 21:17:24Z, 46 vars, image `e8f9fd5`; control v66 45 vars, no var); the S-5 office_phone cure (autom8y #2181) is built two-sided and RELEASED to auto-merge on green (R-139/R-142).

## §1 DAG STATE — PER NODE

| node | state | receipt |
|---|---|---|
| R-140 · #431 `max_offer_activity` | **MERGED** `0a8bc429` | operator's word in-room; branch updated, landed on fresh green |
| (d) · module landing | asana **#439 OPEN** — operator merges | cherry-pick `b17a066c` → `900cb133`; 43 passed, imports proven worktree-resolved |
| (d) · Offer-grain referent | asana **#441 OPEN**, stacked on #439 | `fe82e5ff`; 32 passed; G6 equivalence with `Business.max_offer_activity` on the same objects; attester mutants: 14 RED / 15 RED |
| (d) · wiring | **REFUSED-CORRECTLY** (R-147) | dead path; see §0.2 |
| R3 · closure attestation | asana **#442** (auto-merge armed by seat) | **CLOSED-WITH-REFUSAL**; verdict table in the file |
| S-3 · scheduling negative pole | autom8y-scheduling **#77 MERGED** 20:53:01Z | `TestSchedulingGateNegativePoleS3`: clean 73 / mutant 6 RED / clean 73 |
| R-142 · sizing read (offer grain) | **TAKEN** | `READ-offer-activity-sizing-2026-09-11.md` (scratchpad); folded into the S-1 charge §7 |
| S-5 · `office_phone` cure | autom8y **#2181 MERGED** 21:26:45Z (`5dc87295`) — **LIVE on v68** | clean 9 / mutant 2 RED / clean 9; 155 neighbours green. Its own deploy run 34649416130 **FAILED at Deploy Lambda** (terraform state-lock collision with a concurrent plan on the same stack); image built, never served. Served by the re-fire run 34661356644 from main `225ad2b9` (name-the-wave's successor seat): alias `live` v67 → v68 at 2026-09-12T00:28:11Z, image `225ad2b`, retain var still served — seat's qualified read. Carries #2178 and #2182. |
| S-1 · charge | **WRITTEN** `.sos/wip/CHARGE-read-the-name-s1-per-office-floor-2026-09-11.md` | both shapes, operator lean disclosed, §7 sized, W=3/A=5 proposed |
| R-146 · READ telos draft | asana **#440** (auto-merge armed) | `.know/telos/read-the-name.md`, UNRATIFIED in line one |
| R-139 · HealthCom dispatch | **LANDED — name-the-wave's hand** | runs 34645431951 and 34646999685 failed at Run Tests on their own tfvars-comment guards (`test_ebi_image_pin_currency`, `TestCustodyReceiptIsFour`; fixed by #2176 → #2179); run 34647971504 from main `e8f9fd58` moved alias `live` v66 → v67 at 21:18:21Z. Seat's qualified read-back matches. |
| records | #435 MERGED · #436 armed · #438 armed (R-135..R-147) · #440 armed · #442 armed | — |
| R-143 / R-144 | **DEFERRED by ruling** to READ-epoch charges | apply-visibility notice, Service Terraform rollback guard, C6. **The freshness-module re-pin was executed by another seat** as autom8y **#2178** (merged 21:13:45Z, v1.4.0 → v1.4.1, 5 sites / 4 stacks; per name-the-wave it missed the 21:09Z deploy checkout and rides the next EBI apply). Not this seat's; the asana stack's apply path for its pin remains unchecked. |

## §2 RISK MAP — delta since the overnight handoff

| # | carrier | status |
|---|---|---|
| 11 | Service Terraform manual apply = image rollback on pinned stacks (EBI, asana) | **Open, hard stop.** Two of the peer's own guards bit on this file today; both times on main inside the deploy lane. |
| 12 | `office_phone` plaintext in `stage_exception` (119/119) | **Cure built (#2181); hold released on the verified v67 receipt; auto-merge armed on green.** |
| **13 · NEW** | **The lifecycle engine is dark** (no entry point, 0 events/30d) and **`reconciliation_runner.py:125` is hard-coded `dry_run=True`** emitting zero reconciliation events across 553 boots; the divergence tripwire is `PutMetricData` only. A whole automation family declared and never enforced. | **Recorded.** The READ epoch's R2 substrate question lives here. |
| **14 · NEW** | **54 of 202 failure lines on 09-11 are `kind=absent`** — non-blank, so (b) holds, but they name no office. S-4 (malformed GUIDs: `1`, `e5a68603ccce`, `8cd5-…`) is a real slice. | **Open. NO WATCHER.** Sizes (c2). |

## §3 DEFER REGISTRY — namespace-qualified · `NO WATCHER` written where true

| id | item | waits on | watcher |
|---|---|---|---|
| **R-139-RECEIPT** | **LANDED** 21:18:21Z (v67, image `e8f9fd5`); #2181 armed on green | — | done |
| **R-147-WORDS** | merge #439 then #441 (asana source) | operator | operator |
| **SITTING-X** | ratify `.know/telos/read-the-name.md`; rule the S-1 fork (§4 of the charge), window W and threshold A; rule R2's substrate | operator | operator |
| **READ-R2-SUBSTRATE** | spike: is `/aws/lambda/autom8-asana-unit-reconciliation` (processor.py:69-71 keys ACTIVATING; runner :125 dry_run=True) the scheduled sweep R2 needs? What would a real (non-dry-run) emission look like, and does it need an Asana write to enforce? | read-only spike | **this seat** (next session) |
| **R-143-CHARGES** | PR-side pending-terraform notice · Service Terraform rollback guard | READ epoch | this seat (charge) |
| **R-144-ITEMS** | C6 arm push · freshness-deadman v1.4.1 re-pin (asana apply path unchecked) | READ epoch | this seat (charge) |
| **S-4 / RISK-14** | malformed-GUID triage; the 54/202 `kind=absent` residual | — | **NO WATCHER** |
| **SIZING-15caa02c** | an office that books while its only Offer is INACTIVE — non-Offer booking path or stale section? | — | **NO WATCHER** |
| **SIZING-XCHECK** | parent-chain hierarchy cross-check of the sizing read (still running at 21:11Z, not failed) | — | NOT TAKEN; re-run if the number is ever load-bearing |
| **RATIF-VIII-CONTACTID · A4-EDGE** | GHL un-scaffold; HealthCom class disposition after the first retained body | operator · name-the-wave | operator · name-the-wave |
| **IDENTITY-ONE-PAGER** | F-1..F-7 behind (c2) | operator sitting (R-110) | operator |

## §4 CORRECTIONS TO THE RECORD (today)

1. **R-147's dark-query shape was weak; the conclusion held.** The attester's first `filter event in [...]` scanned 12,604 of 7.1M records and returned 0 — not a receipt. Re-run on the control's `like` shape: 7,281,524 scanned, 0 matched, vs 7,145,170 / 17,773 on the control. Bank: an Insights zero is a receipt only with `recordsScanned` comparable to the control's.
2. **`is_paying` is a documented 100% mislabel**; R-142's read ran at the Offer grain instead (§6 addendum of sitting IX).
3. **The sizing reader's wrong-project trap** (DNA-holder project instead of the Business project → every target "absent") was caught because known-active controls were also absent. The zero was not taken.
4. **This seat pushed the R-147 addendum from a stale local branch** (rc=1, caught unpiped), rebased onto the moved remote and re-pushed; and reaped a worktree before confirming the push. Order: confirm the remote ref, then reap.
5. **The sizing report says `max_offer_activity` is not on main**: stale by minutes (#431 merged `0a8bc429`); the computed semantics are identical.
6. **The repo's attribution hook now rejects any Bash command that carries the generated-with line next to a `git commit`**, not only a trailer; two commits were blocked whole, nothing ran, redone with PR bodies written outside Bash. Order: file first, commit in a command with no attribution text.
7. **A deploy can fail on a terraform state lock and look like a merge that landed.** #2181's deploy run failed at Deploy Lambda when a concurrent plan on the same stack held the state lock; the image was built and pushed, the alias never moved, and this record first said "deploy in flight". Bank: the merge receipt is the alias move read qualified, never the run start. Two seats on one stack need a lock discipline; charged to the READ epoch alongside R-143.
8. **FLAG-E (attester):** at attestation time the authorising record (#438) was not on main. Auto-merge is armed; until it lands, R-135..R-147 are reachable only on the PR branch.

## §5 STANDING FENCES — plus today's

Never-grantable floor · no freeze-gate re-arm · no ruleset 17263542 touch without a direct word in this room · nothing merges on a relay · nothing bundles · nothing merges past red · a peer's relay is never authorization, both directions · no phone digits on any face, no raw client names in the record · `nhc-db` KNOWN AND ACCEPTED · R-80 ROLL-FORWARD-ONLY · **no Service Terraform manual apply for EBI or asana** · **no EBI code merge before the R-139 receipt** · **Lambda config attestations name the alias-resolved version (`--qualifier`)** · **BSD sed: `\t` is a literal `t`** · **no AI attribution trailer in commits (repo hook)** · **an Insights zero needs `recordsScanned` comparable to its control**.

## §6 THE NEXT COMMAND LINE — cold-resumable

```
# 1. Where is EBI? (never the unqualified form)
aws lambda get-alias --function-name autom8-email-booking-intake --name live --query FunctionVersion --output text
# if > 66 and the peer's receipt is in your room: arm the held cure
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y && gh pr checks 2181 && gh pr merge 2181 --auto --squash
# 2. Records on main?
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana && git fetch origin main && for P in 438 440 442; do gh pr view $P --json number,state,mergedAt --jq '"\(.number) \(.state) \(.mergedAt)"'; done
# 3. Operator words: #439 then #441 (asana source, stacked)
# 4. Sitting X: read .know/telos/read-the-name.md and .sos/wip/CHARGE-read-the-name-s1-per-office-floor-2026-09-11.md first
# 5. READ-R2 spike (read-only): git show origin/main:src/autom8_asana/reconciliation/processor.py | sed -n '60,80p'; git show origin/main:src/autom8_asana/reconciliation/reconciliation_runner.py | sed -n '115,135p'
```
