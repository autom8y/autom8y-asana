---
type: decision
status: accepted
artifact_id: RECORD-coc-landing-2026-08-14
wave: chain-of-custody-closure (landing era)
session: coc-phase-2 (session-20260814-090131-e69a1273, resumed)
date: 2026-08-14T09:25Z
rung: LANDED — all three sprints merged + producer-deployed, gate registered + observed biting two-sided
governs: the landing-wave execution record (Phases 0-3). Rules no operator fork; R-5..R-8 governed.
self_assessment_cap: MODERATE
---

# RECORD — coc landing wave (Phases 0-3 execution)

## §1 Entry PV (R-5..R-8, read from `origin/docs/coc-paper-lineage`, now landed via #367)

All SHAs resolved own-hands: CC-5 `coc-cc5-tier1-warm`@`6b75279f` · CC-7 `coc-cc7-gitleaks-gate`@`a922d8f9` · CC-1 #365@`79d9f4a1`. Both code worktrees clean (single-writer PASS). #367 docs-only (15 files, zero non-`.ledge`), all checks green. Scoped-lift dissent noted RECORDED-NOT-RE-LITIGABLE.

## §2 AL-5 re-price — MODEL CORRECTION (LOUD)

UV-P discharge own-hands (`describe-alarms` on `asana-AL5-offer-frame-stale-1143843662099250`, 08:38Z): the inherited "sample window opens ~2026-08-15T12:45Z" has **no ground truth** — the alarm is a ROLLING evaluator (`OfferFrameAgeSeconds`, Max/3600s, 3-of-4 > 7200s, TreatMissingData=missing), config last updated 2026-08-12T11:42Z. It was in **ALARM** at session open (since 08:01:29Z, offer frame age 2.7-3.5h). No discrete window → no cliff; the HALT trigger did NOT fire; soonest-landing = best-landing. R-5's authority unchanged (sovereign; the clock was urgency input and the urgency is confirmed, not refuted — the alarm was firing on the exact staleness surface this wave repairs).

## §3 Phase 1 — the law LANDED

#367 squash-merged manual-on-green **08:40:29Z → origin/main `2ea46474`**. **Deviation from charge letter (LOUD):** "FAST-FORWARD ONLY" was impossible — #367 carried the 7 paper commits REBASED (new SHAs) + landed SQUASHED, so local originals could never FF (R-6's FF prediction fails under rebase+squash). Lossless substitute: byte-equivalence of all 13 paper files verified first (`git diff main origin/main` = 0 lines), then `git rebase --empty=drop origin/main` — 7 commits dropped as patch-already-upstream, autostash clean, no reset. Reflog preserves pre-reconcile tip `1ddfde4d`.

## §4 INCIDENT-1 — 8 exec-lane drafts deleted un-backed-up (owned scar)

Pre-rebase collision cleanup: ~60 untracked local copies of the OTHER lane's (exec-wave #353-#364) artifacts collided with incoming tracked versions; 52 byte-identical, safely dropped; **8 DIFFERED** (`ADR-mission-a-source-of-record`, `CARDS-follow-up-initiatives`, `DEFECT-temporal-filter-imputed-false-move`, `RULING-operator-morning-set`, `HANDOFF-10x-dev-to-sre-ex6-receipt-limb`, `HANDOFF-exec-wave-close`, `NORTH-2026-08-13`, `GATE-pt05-fan-in`). Backup step FAILED SILENTLY (unquoted list var under zsh — no word-split; `mv` errored, 0 backed up) and the cleanup guard checked only existence-on-origin, not identity, so it deleted them. Sibling-checkout recovery sweep: negative. The **landed corrected versions of all 8 are intact on origin/main** (#364 "correct three stale records", #355/#356 rev-2 explicitly superseded stale ones); high-probability the deleted copies were the superseded pre-correction drafts — a probability, not a receipt. **Scar: a cleanup guard must check IDENTITY not existence; a backup step must be receipt-verified (count>0) BEFORE any destructive pass.**

## §5 Phase 2 — serialized merge train (order CC-7 → CC-5 → [register] → CC-1)

Manual-on-green, never `--auto`, update-branch + re-green before each (strict). Pre-merge rite-disjoint NCSR (all GO-WITH-CONDITIONS, zero code-change conditions): #368 CC-7 → platform-engineer[sre] (verified the sha256 pin is the LINUX asset, not darwin — the one NO-GO class, cleared); #369 CC-5 → observability-engineer[sre] (**found what prior critics missed: `OfferFrameAgeSeconds` is a log-metric-filter over the ECS SERVE path, not emitted by this Lambda — the frame-starvation channel is refuted on two independent structural grounds**); #365 CC-1 → audit-lead[hygiene] (identity fence: head still `79d9f4a1`; A-2 new digest-divergence finding, contained).

- **CC-7** merged `cfecbb5a` 09:03Z → satellite-dispatch success 09:09Z.
- **CC-5** merged `43d766f6` 09:10Z → satellite-dispatch success 09:17Z.
- **CC-1** merged `8301ee09` 09:25Z.

## §6 Phase 3 — registration + two-sided bite proof

Registration EXECUTED 09:12Z per RUNBOOK: PATCH `required_status_checks` sub-resource added `Secrets Scan (enforcing)` (app_id 15368); verified n==10, strict/enforce_admins/linear preserved, 9 prior contexts intact. **Ordering law honored** — job observed reporting SUCCESS on main `cfecbb5a` AND on real PR #369 BEFORE the write (no permanently-pending outage).

**Two-sided bite proof:**
- **RED** — synthetic-secret fixture PR #370 → `Secrets Scan (enforcing)` **FAILURE**, mergeStateStatus **BLOCKED**. Fixture retired unmerged, branch deleted.
- **GREEN** — clean #365 → enforcing **SUCCESS**, **CLEAN** mergeable, merged under the registered gate.

**INCIDENT-2 (owned, caught by the discipline):** the FIRST fixture reported a false-GREEN — investigation (own-hands: local gitleaks 8.24.3 proved the token shape trips exit-7; then read the stored blob) found the fixture file content was literally `@-`, not the token: `gh api -f content=@-` uses a RAW field (literal string) where stdin needs `-F` (typed). The gate was NEVER wrong — it correctly passed a file with no secret. Corrected via base64-encoded blob (`-f content=<b64> -f encoding=base64`); the RED then fired. **Scar: `gh api` field-type — `-f` is literal, `-F` reads `@file`/`@-`; a bite-proof RED that passes GREEN is a fixture bug until proven a gate bug, and the discriminator is a local engine run.**

## §7 AL-5 at close (R-9 discipline)

Alarm transitioned **ALARM → OK at 09:13:29Z**. This is **NOT attributed to CC-5**: `OfferFrameAgeSeconds` derives from the ECS serve path (`observability_alarms.tf:446-461`, log-metric-filter over `/ecs/autom8y-asana-service`), which CC-5's Lambda story-warm change does not feed. R-9 trap: a post-deploy green may be the warm fix, the deploy, or natural variance — most likely natural frame-warm variance here. **Segmentation boundaries recorded**: CC-7 deploy 09:09Z, CC-5 deploy 09:17Z; segment all AL-5 readings at these, never average across. Note AL-5 is separately pending re-baseline behind FIX-N-C1 (#339) per `observability_alarms.tf:495-503`.
