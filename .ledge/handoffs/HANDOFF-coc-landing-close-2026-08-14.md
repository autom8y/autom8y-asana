---
type: handoff
status: accepted
artifact_id: HANDOFF-coc-landing-close-2026-08-14
wave: chain-of-custody-closure (landing era)
seam: "PT-05 wave-exit → operator"
session: coc-phase-2 (session-20260814-090131-e69a1273, resumed)
date: 2026-08-14
origin_main: 8301ee09
consumes: "GATE-coc-pt05-2026-08-14 (verdict + POST-RENDER ADDENDUM) · RECORD-coc-landing-2026-08-14 §1-§7 · RULINGS-coc-phase2-operator-sitting-2026-08-14 (R-5..R-9) · REVIEW-pr368/369/365-premerge-2026-08-14"
rules: "RECORDS ONLY — rules NO operator fork; every reserved lever (eunomia limb-(a), CC-8, RE-2 build wave, F-2, FLAG-1, R-CC7-1 triage) stays untouched here"
self_assessment_cap: MODERATE
---

# HANDOFF — chain-of-custody-closure LANDING wave close (PT-05 wave-exit → operator)

**This artifact's own landing route** (pythia, adjudicated by record 13:50Z, verbatim): *"rides the R-6-ratified docs-only route and the landing charge's own stop line — in-scope for this session, no fresh operator merge word; docs-only + manual-on-green fences inherited; any gate bypass remains operator-reserved."*

## §1 Rung roll-call — FINAL

| Sprint | Merge | Producer deploy | Rung |
|---|---|---|---|
| **CC-5** Tier-1 offers-only story-warm (#369) | `43d766f6` 09:10Z | Satellite Dispatch **success 09:17Z** | MERGED + DEPLOY-DISPATCHED |
| **CC-7** gitleaks enforcing job + baseline (#368) | `cfecbb5a` 09:03Z | Satellite Dispatch **success 09:09Z** | MERGED + DEPLOY-DISPATCHED |
| **CC-7 gate** (branch-protection registration) | PATCH 09:12Z, `Secrets Scan (enforcing)` app_id 15368, n==10, strict+enforce_admins+linear preserved, 9 prior contexts intact (`RECORD-coc-landing-2026-08-14.md:41`) | — | **REGISTERED-AND-BITING** |
| **CC-1** swap-detector closure (#365) | `8301ee09` 09:25Z | Satellite Dispatch **success**, run created 09:31:13Z (`GATE-coc-pt05-2026-08-14.md:70`) | MERGED + DEPLOY-DISPATCHED |
| **Paper lineage** (#367, R-6) | `2ea46474` 08:40:29Z | n/a (docs-only) | LANDED |

**Two-sided bite receipt** (`RECORD-coc-landing-2026-08-14.md:43-45`): RED fixture PR #370 → `Secrets Scan (enforcing)` **FAILURE** + mergeStateStatus **BLOCKED**, retired unmerged; GREEN #365 → **SUCCESS** + **CLEAN**, merged *under* the registered gate. This is the STAGED→REGISTERED-AND-BITING promotion PT-04 correctly refused under F-4; it now rests on executed registration + observed bite, not derivation.

**Honest cap.** DEPLOY-DISPATCHED is the fleet-topology ceiling this rite may speak. **Prod-health is rite-disjoint** (eunomia). No deployment-health, regime-change, or user-visible-realization claim is made anywhere in this handoff.

## §2 The stop line — element-by-element, ALL MET

Quoting `GATE-coc-pt05-2026-08-14.md:22-29` with the addendum resolution folded in:

| STOP-LINE element | as-observed | met? |
|---|---|---|
| all three merged | CC-7 `cfecbb5a` 09:03Z · CC-5 `43d766f6` 09:10Z · CC-1 `8301ee09` 09:25Z | **YES** |
| producer-deployed | CC-7 09:09Z · CC-5 09:17Z · CC-1 **09:31Z (was PARTIAL at render; RESOLVED by addendum `:70`)** | **YES** |
| registration executed | 09:12Z PATCH; ordering law honored (job observed SUCCESS on `cfecbb5a` AND on real PR #369 BEFORE the write — no permanently-pending outage) | **YES** |
| observed biting two-sided | #370 FAILURE+BLOCKED (retired) · #365 SUCCESS+CLEAN (merged under it) | **YES** |
| AL-5 state recorded (R-9) | ALARM→OK 09:13:29Z, NOT attributed; segmentation boundaries pegged | **YES** |
| paper durability (R-6) | #367 `2ea46474`; FF impossible under rebase+squash → verified-lossless rebase-drop; deviation RECORDED | **YES (lossless)** |

Verdict carried forward unchanged: **PASS-WITH-CARRIES**. No wall breached, no over-claim, no BLOCK, no back-route, no HALT; the load-bearing-premise PV counter was **not** incremented this wave.

## §3 AL-5 at close

- **Model correction (LOUD, `RECORD-coc-landing-2026-08-14.md:21`):** the inherited "sample window opens ~2026-08-15T12:45Z" has **no ground truth**. `asana-AL5-offer-frame-stale-1143843662099250` is a **rolling** evaluator — `OfferFrameAgeSeconds`, Max/3600s, **3-of-4 datapoints > 7200s**, TreatMissingData=missing. No discrete window ⇒ no cliff; the HALT trigger never fired; soonest-landing was best-landing. R-5's authority is unchanged (sovereign; the clock was urgency input, and the urgency was *confirmed* — the alarm was firing on the exact staleness surface the wave repairs).
- **State:** ALARM at session open **08:01:29Z** → **OK 09:13:29Z** → still **OK at 13:42Z** (datapoints ~4129s < 7200s).
- **NOT attributed (R-9).** `OfferFrameAgeSeconds` is a CloudWatch **log-metric filter over the ECS serve path** (`terraform/services/asana/observability_alarms.tf:446-461`, log group `/ecs/autom8y-asana-service`), which CC-5's **Lambda** story-warmer does not feed — independently re-derived by the rite-disjoint reviewer (`REVIEW-pr369-cc5-premerge-2026-08-14.md:94-116`, Barrier 2). Most likely natural frame-warm variance.
- **Segmentation boundaries (never average across):** CC-7 deploy **09:09Z** · CC-5 deploy **09:17Z** · CC-1 deploy **09:31Z**.
- **Separately pending re-baseline** behind FIX-N-C1 (#339) per `observability_alarms.tf:495-503` — no AL-5 trend reading is comparable across that boundary either.

## §4 Load-bearing carries

- **R-CC7-1 — now MORE load-bearing.** The gate is live, so **every** downstream "history is clean" citation MUST carry it. 31 baseline-masked live-at-HEAD findings, **0 `asana-native-pat`**, cred-t21 fossils absent at HEAD ⇒ benign *now*; dropping R-CC7-1 would falsify any clean-history claim. The gate proves *"no unbaselined finding"*, **never** *"history clean"* (`REVIEW-pr368-cc7-premerge-2026-08-14.md:296-302`). Triage pass **operator-scoped** (DW-COC).
- **FLAG-1 / DW-COC-05 — `ASANA_STORY_WARM_PRIORITY_ENTITIES` is OPERATOR-RESERVED.** The Tier-1/Tier-2 line is now **configuration, not structure**. Operating note added by the rite-disjoint reviewer (`REVIEW-pr369-cc5-premerge-2026-08-14.md:220-236`): the per-entity receipt issues **blocking** `put_metric_data` from inside the async warm loop, so widening the lever to N entities becomes 4N event-loop stalls interleaved mid-warm — reinforcing why the lever stays reserved.
- **eunomia limb-(a) — RIPENED.** Pythia disposition, verbatim: *"RIPENED under both readings of 'LAND' (merged + producer-deploy-dispatched, CC-5 09:17Z / CC-1 09:31Z) — PT-05 §6's open question is moot; eunomia re-invoke is the next act, operator-reserved to fire; this wave attests nothing."*
- **CC-8 — UNBLOCKED.** Its limb-(iii) blocker is cleared: CC-7 is merged, deployed, registered and two-sided-biting (§1). A partial attest is now **schedulable**; this wave schedules nothing.
- **A-1 — CC-1 root exit-note relocation.** `CC-1-EXIT-NOTE.md` sits at repo root against the `.ledge/` convention; post-merge relocation recommended, deliberately not pre-merge (would have voided the C-2 identity fence) — `REVIEW-pr365-cc1-premerge-2026-08-14.md:149-154`.
- **A-2 — digest divergence.** Old delivery-side hash used `ensure_ascii=False`; the new shared canon uses the `json.dumps` default (`ensure_ascii=True`), so digests differ for every real (non-ASCII) payload. Contained (one shared symbol, hashless live emitter, no persisted digest corpus per the CF-2-riding census); one-line docstring disclosure recommended at next touch — `REVIEW-pr365-cc1-premerge-2026-08-14.md:155-165`.
- **iris CARD (R-7)** — `CARD-iris-scope-truth-divergence-2026-08-14.md`, governance-integrity finding, OPEN.
- **RE-2 remediation — RATIFIED, unbuilt.** (f) in-repo `caller_service` allowlist bridge + (a) scope-vocab durable fix, design-may-refine rider, awaiting a **security-seated** build wave. Severity remains **HIGH** (Critical not warranted). The sharpened target governs: the exemption path has no filter; `sa_reconciler.py` re-emits the bypass tuple every boot; the 300s D5 TTL is the sole revocation bound; exempt population drifting upward per NF-1 (`RULINGS-coc-phase2-operator-sitting-2026-08-14.md:40-51`).
- **F-2 (cred-t21 rotation)** — orthogonal, operator convenience; the baseline greens CI, not rotation.
- **INCIDENT-1 data-loss residual** — 8 deleted local drafts unrecoverable by receipt (§5).
- **DW-COC state updates.** **DW-COC-01**: the offers slice is CURED at Tier-1; entities 5-16 remain **starved and unowned** (displacement cost to entities 1-4 is log-only and not alarmable, enforced by the priority gate at `story_warmer.py:204`). **DW-COC-03**: the **in-repo** gate is now LIVE and biting; the **fleet** `|| true` at `autom8y/autom8y-workflows/.github/workflows/security-gitleaks.yml:27` is **untouched** — **locus (a) still open**. DW-COC-02/04/05 unchanged, pegged.

## §5 The two incidents + the wave's scars

- **INCIDENT-1 — 8 exec-lane drafts deleted un-backed-up** (`RECORD-coc-landing-2026-08-14.md:29`). Pre-rebase collision cleanup: ~60 untracked copies of the *other* lane's artifacts; 52 byte-identical and safely dropped; **8 DIFFERED** and were deleted because (i) the backup step failed **silently** (unquoted zsh list var → no word-split → `mv` errored, 0 backed up) and (ii) the cleanup guard checked **existence-on-origin, not IDENTITY**. Sibling-checkout recovery sweep: negative. The **landed corrected versions of all 8 are intact on origin/main** (#364 / #355 / #356 explicitly supersede the stale ones) — high-probability the deleted copies were the superseded pre-correction drafts, **a probability, not a receipt**. Moves no rung; warrants no back-route; carries a data-loss residual. **Scar: a cleanup guard must check IDENTITY not existence; a backup step must be receipt-verified (count>0) BEFORE any destructive pass.**
- **INCIDENT-2 — fixture false-GREEN** (`RECORD-coc-landing-2026-08-14.md:47`). The first bite-proof fixture reported GREEN. Root cause: `gh api -f content=@-` uses a **raw** field (literal string), so the file content was literally `@-`, not the token; stdin needs **`-F`**. **The gate was NEVER wrong** — it correctly passed a file with no secret. Corrected via base64 blob (`-f content=<b64> -f encoding=base64`); the RED then fired. **Scar: a bite-proof RED that passes GREEN is a fixture bug until proven a gate bug, and the discriminator is a local engine run** (gitleaks 8.24.3 locally proved the token shape trips exit-7).
- **Reconciliation deviation (R-6 letter).** "FAST-FORWARD ONLY" was **impossible**: #367 carried the 7 paper commits **rebased** (new SHAs) and landed **squashed**, so local originals could never FF. Lossless substitute executed: byte-equivalence of all 13 paper files proven **first** (`git diff main origin/main` = 0 lines), then `git rebase --empty=drop origin/main` — 7 commits dropped as patch-already-upstream, autostash clean, no reset; reflog preserves the pre-reconcile tip `1ddfde4d` (`RECORD-coc-landing-2026-08-14.md:25`).

## §6 NEW routes opened by this wave

1. **Nightly Live Smoke → /sre + defer-watch peg.** Pythia disposition, verbatim: *"pre-existing standing red — 60/60 scheduled runs failing since 2026-06-16, red since the workflow's 2026-06-11 inception, root-caused to NoCredentialsError (OIDC exchange, upstream of the IAM grant the header hypothesizes), not a required context and not wave-caused. Carried to /sre (OIDC trust-policy wiring) + pegged as a dead-detector watch in the DW-COC-03 family. No back-route."*
2. **StoryWarm alarm follow-on → observability/platform.** From `REVIEW-pr369-cc5-premerge-2026-08-14.md:374-384` (condition 2): `StoryWarmEntity{TaskCount,Success,Failure,Reached}` ship with **zero** terraform consumers — **detection exists; paging does not.** Correctly sequenced behind the zero-terraform-bytes fence, so it is a condition, not a blocker. Recommended: alarm on `StoryWarmEntityReached{entity_type=offer}` **sustained at 0**, and on `StoryWarmEntitySuccess` flatlining at 0 while `StoryWarmEntityTaskCount > 0`.
3. **CC-7 platform-engineer conditions** (`REVIEW-pr368-cc7-premerge-2026-08-14.md:267-294`). **C-1**: `cancel-in-progress: true` also governs the `push: main` leg — house-conventional, not drift, but a cancelled main run must never be mistaken for the observation window; the `post-merge-coverage.yml` precedent (`cancel-in-progress: false`) is the available discriminator. Registration was executed against a run confirmed `success`, so C-1 is discharged for *this* registration and carries forward as an operating note. **C-2**: triggers are scoped `branches: [main]` — a PR targeting any **non-main base** (stacked/release branch) does **not** run the enforcing gate; this coverage boundary should be stated explicitly in the RUNBOOK rather than discovered.

## §7 Operator next-word menu (nothing here is fired by this handoff)

1. **Fire eunomia limb-(a)** — rite-disjoint re-invoke; the ripening precondition is met (§4), the word is the operator's.
2. **Open CC-8 partial attest** — limb-(iii) cleared; schedulable now.
3. **R-CC7-1 triage pass** — the 31 baseline-masked live-at-HEAD findings; until it runs, no "history clean" claim may cite the green gate.
4. **/sre lane** — Nightly Live Smoke OIDC trust-policy wiring **+** the StoryWarm alarm build (§6.1, §6.2).
5. **RE-2 security-seated build wave** — (f)+(a) ratified, awaiting a materialized security bench (Phase-2's never materialized; DEV-1..4).
6. **F-2 cred-t21 rotation** — operator convenience, orthogonal.
7. **Locus (a): fleet `|| true` removal** — the retirement path for the local enforcing fork, per the workflow's own header.

## §8 What this wave did NOT do

No prod-health claim (DEPLOY-DISPATCHED is the ceiling; health is eunomia's). No AL-5 attribution (R-9 held; segmentation boundaries recorded instead). No limb-(a) attestation and no CC-8 attestation (both ripened/unblocked, both operator-fired). No RE-2 re-grade (HIGH stands). No fleet-workflow touch (locus (a) untouched). **No clean-history claim** — R-CC7-1 is attached to every citation of the green gate. No gate bypass — every merge was manual-on-green with `enforce_admins` live, never `--auto`. No re-litigation of the R-5 scoped-lift dissent (RECORDED, not re-opened). No operator fork ruled anywhere in this artifact.

**Evidence grade: [STRUCTURAL | MODERATE].** Single-seat, self-referential authorship capped per `self-ref-evidence-grade-rule`; the landing receipts are corroborated by three **rite-disjoint** pre-merge NCSRs (platform-engineer[sre] #368, observability-engineer[sre] #369, audit-lead[hygiene] #365 — all GO-WITH-CONDITIONS, **zero code-change conditions**) and own-hands SVR anchors, none re-run by this seat.
