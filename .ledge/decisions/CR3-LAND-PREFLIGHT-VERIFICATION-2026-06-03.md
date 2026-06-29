---
type: decision
adr_id: CR3-LAND-PREFLIGHT-VERIFICATION-2026-06-03
title: "CR-3 land pre-flight verification — read-only corroboration of the coordinated-land runbook"
status: accepted
decision_state: PRE-FLIGHT verification — nothing executed (read-only)
rite: sre
date: 2026-06-03
initiative: cr3-fleet-data-plane-foundation-cutover
reversible_only: true
evidence_grade: moderate   # self-ref sre rite, MODERATE ceiling; this is corroboration of the runbook, NOT a land certification
verifies: .ledge/decisions/CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md
synthesis_of:
  - L1 pre-flight invariants P1-P6
  - L2 PR topology + step-a plan
  - L3 #343 traps (Trap-4/Trap-5)
  - L4 OTLP convergence + CPU/mem mechanism
  - L5 section warm lane + knob calibration
  - L6 consumer #55 boundary state
grounding_receipts_this_session:
  - "origin/main HEAD = 3c1dca578808ae2b9dc7729a5339136bbf3aad58 (git ls-remote, this session)"
  - "25d466ca^ == 3c1dca57 (git rev-parse, this session) — rebase cutpoint == main HEAD"
  - "dataframe_max_concurrent_builds ABSENT from src/ (grep exit 1); FROZEN=4 at build_coordinator.py:131"
  - "A8_VERSION = v1.3.8 updated 2026-06-02T18:56:05Z; ECS rev 462 cpu=1024/mem=2048 img :3c1dca5"
  - "Lambda account: 1000 ceiling / 971 unreserved; both asana warmers reserved=1"
---

# CR-3 COORDINATED-LAND PRE-FLIGHT VERIFICATION

> **READ-ONLY corroboration of `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md`. Nothing executed.**
> No merge, no apply, no deploy, no version-cut, no secret op, no push. Every claim below carries a
> file:line / aws-resource / REST-field / exit-code receipt verified at SOURCE this session, or is
> marked UV-P (verify-at-land). Self-ref MODERATE ceiling; this is NOT a land certification.

**Slugs confirmed (`git remote -v`, this session):**
`autom8y-asana` = `git@github.com:autom8y/autom8y-asana.git` (cwd) · `#343` = `autom8y/autom8y`
(REST `.base.repo.full_name`) · consumer `#55` = `https://github.com/autom8y/autom8.git`
(`/Users/tomtenuta/Code/autom8`).

---

## 1. P1–P6 PRE-FLIGHT INVARIANTS — are the runbook's authoring-time receipts still valid at land time?

**Headline: YES — all 6 invariants HOLD at current HEAD. One runbook line-citation has DRIFTED (P2 cosmetic), zero invariant-value drift, zero blockers in this lane.**

| # | Invariant | Verdict | Live receipt (verified at SOURCE this session) |
|---|-----------|---------|-----------------------------------------------|
| P1 | origin/main HEAD == `3c1dca57` | **PASS** | `git ls-remote origin refs/heads/main` → `3c1dca578808ae2b9dc7729a5339136bbf3aad58`. Matches runbook grounding_receipt. All 4 main-based receiver PRs pin `base.sha=3c1dca57`. |
| P2 | `max_concurrent_builds` FROZEN=4 | **PASS (value) / DRIFTED (cited line)** | VALUE holds: `build_coordinator.py:131` → `max_concurrent_builds: int = 4` (grep exit 0); semaphore at :141. Co-bound sizing comment at `settings.py:273`. **DRIFT:** runbook P2 cites `settings.py:305` — no FROZEN=4 evidence there; the parameterizing field `dataframe_max_concurrent_builds` is ABSENT from current main src (grep **exit 1** — arrives only with unmerged PR #100). Invariant satisfied; runbook line citation is wrong (cosmetic, non-blocking). |
| P3a | A8_VERSION repo var == `v1.3.8` | **PASS** | `gh api repos/autom8y/autom8y/actions/variables/A8_VERSION` → `value:"v1.3.8"`, `updated_at:"2026-06-02T18:56:05Z"`. Exact match. |
| P3b | applied baseline cpu=1024/mem=2048 | **PASS** | `aws ecs describe-task-definition autom8y-asana-service` → active rev **462**, `cpu=1024`, `mem=2048`, status ACTIVE, image `…/autom8y/asana:3c1dca5` (== main HEAD short-SHA, NOT `latest`/digest). Correct pre-LEVER state. |
| P4 | all receiver PRs OPEN, merged=false | **PASS** | All six `state=open`, `merged=false` (REST GET each). Heads: #98 `e85e111a` (base main), #99 `8d85f59d` (base main), #100 `938fa8eb` (base main), #101 `66490ca0` (base main), #102 `47e93ede` (**base=`sre/serve-stale-…-2026-06-03`=#99 head `8d85f59d`** → stacked-on-#99 CONFIRMED), #103 `c05092c4` (base main). |
| P5 | #343 cred-surface OPEN, head `255f25ae` | **PASS (topology) / UV-P (0-destroy)** | `gh api repos/autom8y/autom8y/pulls/343` → `state=open`, `merged=false`, head `255f25ae`, base main, baserepo `autom8y/autom8y`, `changed_files=1`. The 0-destroy/Trap-4 plan signature is **UV-P** — requires the land-time re-plan (runbook §0 P5 + step c defer it explicitly). |
| P6 | consumer #55 head `09e0f64b` | **PASS** | `gh api repos/autom8y/autom8/pulls/55` → `state=open`, `merged=false`, head `09e0f64b`, base main, baserepo `autom8y/autom8`, `changed_files=3` (≡ local `ae41170c` by patch-id `a04ac55e…` per prior rite-disjoint V1). |

---

## 2. PER-GATE READINESS (IC-GATE 1–7)

Each gate: **READY** / **BLOCKED** / **UV-P-until-land**, with the gating receipt and the land-time check that must confirm.

| Gate | Step | Verdict | Gating receipt (this session) | Land-time check MUST confirm |
|------|------|---------|-------------------------------|------------------------------|
| **IC-GATE 1** | (b) merge #98→#100→#99→#101→#102 | **READY** (after step-a rebase) | #98/#99/#100/#101 all `mergeable_state=clean`, 7 Test check-runs each = success/skipped (REST `commits/{sha}/check-runs`). #102 stacked, retargets to main on #99 merge. | Each merge → `merged=true`; main-Test green BEFORE next merge; quiesce in-flight satellite dispatches between merges (PR #94 serializes). |
| **IC-GATE 2** | (c) `terraform apply` #343 | **UV-P-until-land** | Structure PASS (L3): 1 file `dataframe_resolver_creds.tf` status=added; Secret 1 + 2 SSM pointers + clientid-drift alarm; exactly **3 `import{}` blocks**; **0** `aws_secretsmanager_secret_version` resource blocks. Trap-5 image derives live to `3c1dca5` (ECS rev 462 + running task + ECR tag). | Re-plan shows **`+0 DESTROY` on cred surface** (Trap-4); pass `-var image_tag=3c1dca5 -var image_ref=:3c1dca5 -var environment=production` (Trap-5); post-apply clean re-plan `0/0/0`. STOP if any destroy on `*resolver*` Secret/SSM. |
| **IC-GATE 3** | (d) C1 5-lambda OTLP convergence | **UV-P-until-land** | Divergence REAL (L4): SSM `…/grafana-tempo-otlp-headers` Version=10 @`2026-06-03T12:59:27Z` vs 5 asana-lambda env baked @~`09:06Z` (~3h53m skew). 5 lambdas: cache-warmer, cache-warmer-bulk, insights-export, conversation-audit, unit-reconciliation. | Post re-bake from SSM v10, re-plan asserts literal **`0 to add, 0 to change, 0 to destroy`** on observability/lambda-env surface. |
| **IC-GATE 4** | (e) CPU/mem → 2048/8192 (LEVER) | **UV-P-until-land** | Mechanism PASS (L4): a8-manifest overlay path (`cmd/a8/deploy.go:845-847`), NOT autom8y TF apply (asana service `ignore_changes=[task_definition]`). **DRIFT (L4): canonical `/Users/tomtenuta/Code/a8/manifest.yaml` `services.asana.resources` = cpu:256/mem:1024**, drifting from runtime 1024/2048 AND runbook baseline — operator must edit the LIVE-baseline-correct manifest, not assume 1024/2048 in source. | Edit manifest → 2048/8192; cut a8 tag (v1.3.9); bump A8_VERSION v1.3.8→v1.3.9; satellite deploy; verify at RUNTIME `describe-tasks` → cpu=2048/mem=8192 HEALTHY (NOT the TF plan). |
| **IC-GATE 5** | (g) deploy §B SECTION warm lane | **BLOCKED (greenfield — must build) / budget READY** | Lane is **NOT BUILT** (L5 + this session): `section_only_prematerialization_keys` / `prematerialize_section_set` grep **exit 1** across src/. Generic driver `_prematerialize_bulk_set_async(…, key_source, fast_lane)` exists (cache_warmer.py:247) — section is a 3rd `key_source` + flag + disjoint prefix away. **Budget READY:** `aws lambda get-account-settings` → 1000 ceiling / **971 unreserved**; both warmers reserved=1. Carving a 2–3 section pool has massive headroom — no budget blocker. | Build section lane (greenfield, runbook step g); deploy with OWN reserved-concurrency pool (≥2–3, disjoint from bulk's =1); disjoint `CACHE_WARMER_CHECKPOINT_PREFIX`; ≤10-min EventBridge. Re-verify acct budget at build-plan time. |
| **IC-GATE 6** | (h) calibrate knob → `{"project":86400,"section":576}` | **UV-P-until-land** | Knob ships inert `{}` via #99; #102 carries the calibration map (stacked). `section`=576 == `caching.py:39 SECTION_DF_REFRESH_HOURS=0.16×3600`. Only `project`/`section` bind a receiver entity_type; analytics/backfill/vertical-summary are DEAD KEYS (exclude). | Deployed `FRESHNESS_CONTRACT_MAX_AGE_SECONDS == {"project":86400,"section":576}` (no extra keys); a section read <576s old serves FRESH/SWR. MUST follow step g (lane live) or build-storm. |
| **IC-GATE 7** | (j) merge consumer #55 | **UV-P-until-land (cross-repo, gated on §D)** | #55 boundary PASS (L6): open/unmerged, head `09e0f64b`, 3 files (`section/main.py`, `satellite_config.py`, `test_resolver_auth_config.py`); H-2 `if _flag_enabled is False:` at `section/main.py:679`; honest-gate `is_honest_frame` at :819; 3 fail-safe nets in tests. | §D ≥99% re-gate PASS (chaos-engineer, rite-disjoint, headroom-applied substrate) AND consumer QA re-gate green; THEN `merged=true`, live monolith fetches Secret 1 (HTTP 200). |

**Note — #103 (`fix/section-missing-selector-guard`, head `c05092c4`): NOT in the CR-3 merge order.** It is OPEN, `mergeable=true` but `mergeable_state=blocked` with a CI `failure` conclusion (REST check-runs returns `["failure","skipped","success"]`). It is **out-of-scope** for steps a/b — not a gate blocker for this land, but must not be swept into the merge sequence.

---

## 3. VERIFIED STEP-a REBASE PLAN — what the main thread executes next (reversible, NO gate)

All SHAs and branch names confirmed at SOURCE this session. **`25d466ca^` resolves to `3c1dca57` (== origin/main HEAD)** — `git rev-parse 25d466ca^` confirmed — so `--onto origin/main 25d466ca^` strips exactly the two fast-lane commits (`25d466ca` + `873653e7`) and grafts the branch's logical change onto current main, interposing nothing.

**Runbook branch-name drift corrected:** runbook step-a says `sre/serve-stale-adr-stale-served-knob` and `sre/calibrate-freshness-knob-oq2`; the ACTUAL origin branches carry the `-2026-06-03` suffix (confirmed via `git ls-remote`). The commands below use the VERIFIED names.

```bash
git fetch origin

# #99 — carries fast-lane delta (25d466ca + 873653e7); rebase onto main
git rebase --onto origin/main 25d466ca^ sre/serve-stale-adr-stale-served-knob-2026-06-03

# #100 — carries delta; rebase onto main
git rebase --onto origin/main 25d466ca^ sre/cr3-c2-namespace-pq1-headroom-prep

# #101 — carries delta; rebase onto main
git rebase --onto origin/main 25d466ca^ sre/canary-project-arm-content-binding

# #102 — STACKED on #99 (base = #99 head 8d85f59d). Rebase AFTER #99's rebase lands.
#         <old-99-head> = 8d85f59d (current #99 tip == #102 current base_sha, REST-confirmed).
git rebase --onto sre/serve-stale-adr-stale-served-knob-2026-06-03 8d85f59d sre/calibrate-freshness-knob-oq2-2026-06-03
```

**#98 and #103 are already clean** (base main, do NOT carry the fast-lane delta per L2) — no rebase.

**Per-branch verify (after each rebase, before push):**
```bash
git diff origin/main...<branch> --stat   # MUST contain ONLY the branch's logical change —
                                         # NO fast-lane handler files (*fast_lane*, 15-min section/fast key source)
```
**Abort:** if a rebase surfaces a conflict in the fast-lane files, STOP — the delta separation is wrong; re-derive the bundling root before continuing.

> Step-a is a branch op (reversible, no IC gate). Pushing the rebased branches is the reversible
> prep that precedes IC-GATE 1. The push itself is out of THIS read-only pass's authority.

---

## 4. DRIFT / BLOCKERS

**No hard blocker to step-a or to presenting IC-GATE 1.** Drifts found (none invalidate an invariant; all must be noted to the operator):

| ID | Severity | Drift | Resolution before gate |
|----|----------|-------|------------------------|
| D1 | Cosmetic | Runbook P2 cites `settings.py:305` for FROZEN=4 — that line is unrelated ASANA_CACHE_TTL fallback. Real anchors: `build_coordinator.py:131` + `settings.py:273` comment. | None required — invariant value (=4) holds. Correct the citation if the runbook is re-issued. |
| D2 | Operational | Runbook step-a branch names lack the `-2026-06-03` suffix on #99 and #102; actual origin branches carry it. | **Resolved in §3** — verified commands use actual names. Operator MUST use §3 commands, not the runbook's literal step-a block. |
| D3 | Operational (GATE 4) | Canonical a8 `manifest.yaml services.asana.resources = cpu:256/mem:1024` (L4), drifting from BOTH live runtime (1024/2048) and runbook baseline (1024/2048). | At step e, operator edits manifest to 2048/8192 anyway, but must NOT assume the in-source baseline is 1024/2048. Land-time verify at RUNTIME via `describe-tasks`. |
| D4 | Scope guard | #103 is CI-red (`mergeable_state=blocked`, `failure` check-run) and is NOT in the CR-3 merge order. | None for this land — must NOT be merged in step b. Flagged so a "blocked PR" surprise doesn't derail the sequence. |
| D5 | UV-P (not drift) | #102 has **0 Test check-runs** (`commits/{sha}/check-runs` count=0) — CI never ran against an independent base because it is stacked on #99. | CI must run+green AFTER #102 is restacked onto post-rebase #99 and retargeted to main. Verify-at-merge (IC-GATE 1). |

**Not-found blockers (explicitly cleared):** main has NOT moved (P1 stable `3c1dca57`); no merge-order PR is dirty/behind (#98/#99/#100/#101 all `clean`); no rate-limit hit (all checks via REST, no GraphQL); account budget CAN carve the section pool (971 unreserved ≫ 2–3 needed — GATE 5 budget READY).

---

## 5. GO / NO-GO

**(a) Execute step-a (rebase #99/#100/#101 onto main; restack #102 onto #99) NOW: GO.**
Fully reversible, no IC gate. Rebase cutpoint `25d466ca^ == origin/main 3c1dca57` confirmed; all 5 branches exist on origin at the expected heads; the two fast-lane commits exist and are the exact delta to strip. Use the §3 VERIFIED commands (corrected branch names), with the per-branch `--stat` verify and the fast-lane-conflict abort.

**(b) Present IC-GATE 1 to the operator: GO — conditional on step-a completing clean.**
#98/#99/#100/#101 are `mergeable_state=clean` with green Test check-runs; the merge order and dependency topology (incl. #102-stacked-on-#99) are source-confirmed. Conditions to surface at the gate: (i) re-confirm main-Test green on each branch's head after the rebases push; (ii) #102 CI must run+green post-restack (D5); (iii) exclude #103 from the merge set (D4); (iv) carry forward the P2 citation drift (D1) as cosmetic-only.

**Downstream gates (IC-GATE 2–7) are UV-P-until-land by design** (Trap-4 re-plan, OTLP 0/0/0, runtime cpu/mem, section-lane build, knob deploy, §D re-gate) — each enumerated in §2 with its land-time check. **IC-GATE 5 additionally requires BUILDING the section lane** (greenfield, grep exit 1) before it can be presented — it is not a present-and-approve gate yet.

> Self-ref MODERATE ceiling. This artifact is read-only corroboration of the runbook's receipts at
> land time, NOT a land certification. STRONG claims belong to the rite-disjoint sources (consumer #55
> V1 patch-id, OQ-1/OQ-4) cited in the runbook, and to the §D chaos-engineer re-gate (IC-GATE 7).
