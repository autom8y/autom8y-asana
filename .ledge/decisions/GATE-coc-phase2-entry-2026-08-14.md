---
type: decision
status: accepted
artifact_id: GATE-coc-phase2-entry-2026-08-14
wave: chain-of-custody-closure
checkpoint: PHASE-2 ENTRY — premise-validation entry-gate on the inbound handoff+rulings PAIR
rendered_by: potnia (10x-dev, Read-only; main thread owns git, persistence, and all dispatches)
date: 2026-08-14
verdict: PASS-WITH-CORRECTIONS
origin_main: d7560153 (re-pinned own-hands by dispatcher — IDENTICAL to the handoff pin)
scope_fence: rules NO operator fork. F-1/F-7/F-8/CC-7-opening were ruled by the OPERATOR (R-1/R-3); F-2, F-4, GATE-FORK, RE-2 remediation + severity re-grade, and every merge word remain operator-reserved and untouched here.
self_assessment_cap: MODERATE (single seat, self-referential; dispatcher receipts un-corroborated by a second reader)
---

# GATE — chain-of-custody-closure PHASE-2 ENTRY

## §1 ENTRY VERDICT — **PASS-WITH-CORRECTIONS**

Per-premise grading of the dispatch brief. `own-eyes` = read by this seat this sitting; `SVR-dispatcher` = main-thread own-hands receipt, graded MODERATE (mechanical command, single seat, no rite-disjoint second read).

| # | premise | PV | grade | note |
|---|---|---|---|---|
| P-1 | R-1..R-4 exist as the four operator words | **TRUE** | own-eyes | `RULINGS…:16-60`. All four unambiguous |
| P-2 | rulings COMMITTED at `464266a5` (Phase 0) | **TRUE** | SVR-dispatcher / MODERATE | not verifiable by this seat (no Bash) |
| P-3 | HANDOFF §6 duplication defect owned | **TRUE** | own-eyes | `HANDOFF…:76-78`; becomes a Phase-2 wall (§4) |
| P-4 | GATE-coc-pt03 lives at `.ledge/reviews/` | **FALSE** | own-eyes | **CORRECTED — minor-locational**: actual path `.ledge/decisions/GATE-coc-pt03-2026-08-13.md`. Content resolved on first probe; NOT load-bearing (no claim rests on the directory). Downstream citations must be repaired |
| P-5 | `CRITIQUE-cc6…:99-149` = AR-1 / MC-1 | **TRUE** | own-eyes | **CONFIRMED READABLE AND EXACT**: §2.2 opens at `:99`, the AR-1 verdict closes at `:148-149`. This is the load-bearing CC-7 ingestion range |
| P-6 | "main has ADVANCED" since the handoff pin | **FALSE** | SVR-dispatcher | **CORRECTED own-hands**: `origin/main = d7560153` = the handoff pin (`HANDOFF…:8`). What is stale is the **LOCAL checkout** (12 behind; #353–#364 exec-wave of 2026-08-12), now 1-ahead/12-behind un-pushed. Class = substrate-of-record read-surface error (local tree ≠ origin/main). **Consequence is favourable**: no re-pin cascade; every Phase-1 artifact's grounding at d7560153 STANDS |
| P-7 | PR #365 OPEN, un-armed, CI observed | **TRUE** | SVR-dispatcher | head `79d9f4a1`, `autoMerge=false` ✓, mergeStateStatus CLEAN, 28 contexts SUCCESS/SKIPPED |
| P-8 | AL-5 window ~2026-08-15T12:45Z; ~29h45m runway; NOT closed | **TRUE-AS-UV-P** | SVR-dispatcher on a **UV-P** referent | the window-open timestamp was never re-verified own-hands (`SLATE…:204-206`, label confirmed correct by the critic). The runway is a UV-P-graded quantity — it must not harden into fact in any Phase-2 artifact |
| P-9 | `merge-tree origin/main coc-cc1-reconverge` CLEAN | **TRUE** | SVR-dispatcher | no conflict debt |

**Tripwire accounting**: the one load-bearing-class falsehood (P-6) was corrected **own-hands before entry**, and no artifact was authored on it. Load-bearing-premise PV-FALSE counter **NOT incremented**; no Pythia consult required. Recorded so a recurrence is detectable — had P-6 been inherited un-probed, it would have fired.

**RUNG ADVANCE CONFIRMED**: R-4 conditions the rung on CI observation (`RULINGS…:57`). CI is now observed. **CC-1 advances `rung-BUILT-DARK` → `rung-PR-UP-MERGE-HELD`.** Two anti-overclaim fences ride with it: (i) the advance is a *publication* rung, not a live-emitter closure — N2 clause-4a stays UNATTESTED and CF-2 stays UV-P; (ii) the green `gitleaks / Secrets Scan` context is **NOT** evidence of a passing secrets scan — it is the `|| true` always-green (`CRITIQUE-cc6…:93-94`), i.e. the exact fossil CC-7 exists to kill.

## §2 PHASE-2 SEQUENCING — **CONFIRMED, with two amendments**

- **CC-5 dispatches FIRST — sole clock edge. CONFIRMED**, with **AMENDMENT A**: CC-5's clock *value* is contingent, not owned by the sprint. "Landed before the window" means **merged + deployed**; F-4 is unlifted and no merge word exists (`RULINGS…:58-59`). CC-5 therefore buys a **merge-ready artifact**, never a clean AL-5 regime. Its exit rung ceiling is `rung-BUILT` / `PR-UP-MERGE-HELD` — any "clean regime secured" claim is an over-claim and must be refused at CC-5's exit.
- **CC-7 ∥ SEC-002. CONFIRMED.** Path-disjoint by construction (CC-5 → `src/`; CC-7 → `.github/workflows/` + `.gitleaksignore`; SEC-002 → cross-repo read-only). Single-writer per path holds across the three-wide fan.
- **Edge CC-7 → CC-8 ONLY. CONFIRMED** (`HANDOFF…:32`; `GATE-pt03 §5:59-60`), with **AMENDMENT B**: CC-8 is at best *partially* reachable this session — limb (iii) rides CC-7, but limb-(a) is eunomia's and BLOCKED until both WS-A halves **LAND** (not merely build). Under F-4, limb-(a) is unreachable. CC-8 must be dispatched (if at all) as a partial attest at HELD rungs, never as wave closure.
- **SEC-002 gates nothing. CONFIRMED** — it fixes severity, not a rung. It *does* gate one thing: **no seat may re-grade RE-2 before it reports** (R-2).
- **PR #365 = standing main-thread observation, not a sprint. CONFIRMED.** No agent seat owns it; no agent touches git or auto-merge.

## §3 BINDING CARRIES — per sprint, name-checked at dispatch

**CC-5** (Tier-1 offers-only, ~4,192 tasks, one Lambda, one project GID — coc lane owns per R-1):
- **CF-8 + DF-4** — any WS-C fix is a *producer deploy* that re-arms AL-5; mechanism `cache_warmer.py:1159-1166` (story warming shares the frame warmer's invocation and `context`). The window timestamp is **UV-P**.
- **R-9 trap, verbatim** — do not misread a post-deploy AL-5 green as staleness cured; it may be the warm fix or the deploy, not the regime (`SLATE…:214-216`).
- **Tier 2 FORBIDDEN** (R-1; `DW-COC-01` pegs it). A Tier-1 price must not smuggle a Tier-2 commitment (`SLATE…:120-121`).
- **FR-3 corrected anchors** — `story_warmer.py:157` (NOT `:159`); `stories.py` def-site + `:97-98`/`:100` (NOT `:34`/`:30`).
- **A.4 hazard** — the imputed payload is visually indistinguishable from an observed one, and 4,192 misses ≫ 50 takes the no-op branch so the call writes nothing (`section_timeline_service.py:505/:532`). Disclosure duty survives until a warm is *proven* to reach offer.
- **CF-3** (offer-GID-shared-with-a-warmed-entity null, unresolved by both parties) and **CF-18** (warm_priority tie-fragility) must not be assumed away.
- **Lever selection is NOT operator-reserved** — `GATE §A.5` conditions CC-5's opening on ownership AND scope only, and R-1 supplied both. The lever is CC-5's engineering call *inside the Tier-1 fence*, and the dispatch must carry the DF-4 pricing so it is made knowingly: O-A/O-C give one clean boundary; O-B/O-F give a **fuzzy** boundary + highest O-7a cost; O-D needs a demand signal that does not exist; O-G is low-confidence and adds a 429 confound.

**CC-7** (two-action boundary per R-3):
- **MC-1 / AR-1** — locus (c) is **two actions**: local enforcing job **+** branch-protection contexts registration. Shipped as one action it *is* the silent non-biting gate this wave exists to close. **Must ingest `CRITIQUE-cc6-gitleaks-recon-2026-08-13.md:99-149`** (confirmed readable) alongside `RECON…:192`.
- **CF-5** — the baseline is **fingerprint-keyed** (`commit:file:rule:line`), not commit-SHA-keyed, and must cover the **FULL historical tripping set**, not only cred-t21's three commits. The *baseline* unblocks CI; the rotation does not (F-2 is orthogonal, untouched, operator-only).
- **CF-4** — CR-5 regex residual: `asana-native-pat` validated against synthetic shapes only; deviation from the documented shape means the rule silently does not fire. One-sided: could trip *less*, never more. Uncloseable without reading the credential (CR-5 forbids).
- **AR-1 mode-2 ordering hazard** — register the context **AFTER** the job LANDS, never before; a registered-but-unreportable context blocks every merge the instant the fence lifts.
- **F-4 CONSEQUENCE (LOUD)** — no merge word exists, so the job **cannot land this session**, so **the registration CANNOT execute this session**. CC-7's registration half is **AUTHORED / STAGED ONLY**: a runbook carrying the exact context string, flagged repo-admin + operator-reserved. Exit ceiling: job half `PR-UP-MERGE-HELD`, registration half `rung-STAGED`.
- **CC-7 CANNOT reach a biting gate this session.** Its shape exit criterion 1 ("the red path reaches the surface that actually blocks a merge") is structurally unreachable under F-4 — see BR-3.
- Bounded: **CF-19** (option-(a) org blast radius, unenumerated — (a) is not this locus per R-3), **CF-20** (cred-t21 code-scanning alert not queried, CR-5).

**SEC-002** (charge per R-2 — severity only, gates no rung):
- **CF-1 is ALREADY YES at the registry layer** (`ace` + `iris` both `business_scoped: false`, Bucket 1, formal `exemption` blocks, `category: ai_agent`, `approved_by: tomtenuta`, 2026-04-11/2026-04-13, TENSION-005 mitigated via D5 5-min TTL, read-only scope sets). The charge is therefore **NOT** to re-answer the yes/no — it is the **CHAIN trace: registry → OpenFGA tuples (`can_issue_service_token` / `bypass_scope_enforcement`) → issuance-time behaviour**.
- **CF-1 widening** — `iris` carries no asana scope in the SA registry but the same logical identity holds `asana:read` via OAuth-client terraform (`module oauth_clients_hermes`): a **second uncounted population** beyond the design's 18. `iris` is precisely the seat where the two substrates disagree.
- **CF-6** — UV-P-3 species reclassification: structural half CONFIRMED (SERVICE is an unguarded catch-all `else` with no `token_type` allowlist; `agent_access` is silently reclassified as `ServiceClaims`, `client.py:L476-489`); remaining half = audience + mintability.
- **RE-2 F-001 stays HIGH until SEC-002 reports. NO re-grade by any seat** (R-2, explicit). Determinant-YES receipts attach to `DW-COC-02`.
- CR-5 binds: static config/code read, **never** a token mint. **CF-7 is adjacent but NOT this charge** — widening it is the operator's word, not SEC-002's self-assignment.

## §4 HARD WALLS — restated for the record

1. **F-4 / no-merge.** No merge word exists (R-4 withheld it pending AL-5 re-pricing). No seat merges, deploys, pushes, or arms auto-merge. PR #365 stays un-armed (`autoMerge=false` verified). `enforce_admins: true` — never `--auto`.
2. **MODERATE self-cap.** Every seat's self-assessment ceiling is MODERATE. STRONG only via a rite-disjoint second read and only **leg-scoped**. No critic grades its author STRONG.
3. **Single-writer per path.** The §6 duplication defect is owned: under API instability, retries spawn duplicate writers on shared paths. Code/shared-path sprints require a single-writer guarantee + anti-collision guard; paper sprints are last-writer-wins-tolerant. Keep every clock on the main thread — a self-parked background subagent does not resume.
4. **limb-(a) is eunomia's alone**, BLOCKED until both WS-A halves **LAND** (not build) → unreachable this session.
5. **CF-2 UV-P.** CC-1's hashless-live-emitter census was NOT re-probed; it rides as UV-P, not fact, and becomes live the moment EX-5 ships `report_generated` while REC-002 stays undone. The rung advance in §1 does not touch it.
6. **CF-7 UNKNOWN.** `/api/v1/tasks/*` and `/api/v1/projects/*` are JWT-excluded and publicly enumerated **including DELETE**; posture UNKNOWN. No seat may assert the mutation surface is bounded to the five write classes.
7. **Operator-reserved, untouchable by any seat**: F-2 (rotation), F-4 (fence lift), GATE-FORK, the RE-2 remediation *and* any severity re-grade, every merge word, and the branch-protection registration **execution**. Also standing: no credential read (CR-5), CR-1/CR-2 untouched, main thread owns git.
8. **Substrate of record = `origin/main` (d7560153), never the local checkout** — which is 12 behind. This is the exact surface that produced the corrected P-6. Every Phase-2 seat grounds reads on origin/main.

## §5 BACK-ROUTES, FLAGS, AND ESCALATIONS

- **BR-1 (carry migration, not a halt).** `GATE-pt03 §5:62` made the FR-3 anchor repairs a precondition *"before CC-4's slate reaches the F-1 fork."* The fork was ruled 2026-08-13 with the anchors unrepaired — the precondition was missed. Immaterial to R-1 (the repairs are declared non-material and every substantive claim was independently re-derived through a different route). **The repair duty MIGRATES to CC-5's ingestion** (§3).
- **BR-2 (locational).** Repair the `GATE-coc-pt03` citation path to `.ledge/decisions/` in the Phase-2 brief and in any downstream artifact. No re-authoring.
- **BR-3 (LOUD — highest over-claim risk in Phase 2).** CC-7's shape exit criterion 1 is **UNREACHABLE under F-4**. Dispatched against the unamended criteria, CC-7 will either over-claim a biting gate or halt at its own exit. **Amend CC-7's exit criteria AT DISPATCH** per §3 (job → `PR-UP-MERGE-HELD`; registration → `rung-STAGED` runbook).
- **BR-4 (LOUD — operator escalation, NOT ruled here).** The AL-5 "one clean regime" prize is likely already unpurchasable inside the runway: it requires CC-5 build + rite-disjoint critique + an operator merge word + merge + deploy + a warm cycle within ~29h45m of a **UV-P** deadline, while F-4 is unlifted and no merge word exists. **Surface to the operator as a decision-quality input, not a pressure**: either the merge+deploy word comes early enough, or O-7a segmentation is the expected outcome and CC-5 should be dispatched on its engineering merits rather than its clock. **This seat rules nothing here** — the runway decision, like F-4, is the operator's.
- **BR-5 (composition).** Phase 1 drew 3/5 second-readers from **arch** (flagged at `GATE-pt03:26`). Spread Phase-2 critique across security / sre / eunomia / arch; `qa-adversary` critiqued nothing in Phase 1 and remains available. Preserve rite-disjointness 1:1 and check no barred seat.
- **BR-6 (hygiene).** The `PROBE-re2-blast-radius` rung-less-`status: complete` shape (`GATE-pt03 §2.1`) must not recur. Every Phase-2 artifact carries an explicit `rung:` field.
- **No HALT at entry.** Phase 2 is CLEARED to dispatch on the §2 sequencing with the §3 carries, the §4 walls, and the BR-3 exit-criteria amendment applied at dispatch time.
