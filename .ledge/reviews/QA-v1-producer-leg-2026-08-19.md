---
type: review
status: accepted
title: QA — SPR-V1 producer leg (PR autom8y-asana#384), adversarial verification
initiative: asr-verification-axis-landing
sprint: SPR-V1
rite: 10x-dev
author: qa-adversary
created: 2026-08-19
verdict: GO-WITH-NOTES
evidence_grade: MODERATE
grade_ceiling_reason: >-
  Single-attester QA, same-rite as the builder. All receipts re-derived
  first-hand (own worktree of the PR head, own production probes, own
  mutations), but ADVISORY §C.5 binds: same-rite convergence caps at MODERATE.
  SPR-VC remains the disjoint attester.
pins:
  pr_head: 220829ecbc2f292cb8c8c68260878fb0db2ceb1f
  branch_point: e3aab8d47e932d8d46588fc62e6a4906d7712c4a
  origin_main_at_qa: "8098d307 (#383, advanced past the branch point during QA)"
  probed_at_utc: "2026-08-19T17:07Z – 17:35Z"
production_change: NONE (this QA is read-only; the MERGE is the production act)
---

# QA — SPR-V1 Producer Leg (PR #384)

> **VERDICT: GO-WITH-NOTES.** No critical or high defect found. The dormant
> path is byte-identical on the 20 baseline keys; the before-trace re-verified
> first-hand against live production; every hostile input fails in the REFUSE
> direction, never toward a false-GREEN; 16603/16603 unit tests green in my own
> run; 4 QA-authored mutations (disjoint from the builder's 14) all bite.
> Three LOW defects and three NOTES below — none merge-blocking, two of the
> notes are operational facts the merge actor must hold.

Method: own worktree of `refs/pull/384/head` (`220829ec`) under the QA
scratchpad; base worktree at `e3aab8d4` for A/B serialization; read-only
production probes (ECS, Secrets Manager read, two authenticated POSTs — the
exact consumer tick); broken INPUTS only; zero production-source edits
(mutations applied-run-reverted in the QA worktree only, worktree restored
clean to the PR head afterward).

---

## §1 Attack-surface results (8/8 discharged)

| # | Surface | Result |
|---|---|---|
| 1 | Dormant-path byte identity | **PASS.** A/B dump (base `e3aab8d4` vs head), same 20 baseline values through `model_dump(mode="json", by_alias=True)` — all 20 keys byte-identical in value AND type; declared field order preserved; the 4 new fields append after `column_manifest`. `AggregateMeta` likewise additive-only. Route decorators and `SuccessResponse` envelope carry **no** `exclude_none`/`exclude_unset`/`exclude_defaults`/alias flags (repo-wide grep: the only `exclude_*` uses are on the resolver/saved-query/intake lanes, not the query route). |
| 2 | Serializer betrayals | **PASS.** `verification_backfill_used=false` and `verified_at=null` survive serialization (asserted on serialized JSON in `tests/unit/query/test_verification_axis.py:238` and reproduced by my dumps). `verified_at` is offset-bearing UTC isoformat. Epoch-zero stamp → age ≈ 1.787e9 s (derives, honestly ancient). Far-future stamp → NEGATIVE age, unclamped, disclosed — per TDD §5.4. Naive stamp → refuses (see DEF-1 for the mechanism). |
| 3 | Hostile manifests | **PASS — every arm fails toward REFUSE.** Empty manifest → AXIS-NULL. Only-null-named entries → AXIS-NULL (scoped and whole-frame). All-unstamped → AXIS-NULL + backfill=true. Duplicate names mixed stamped/unstamped → over-refusal (AXIS-NULL), never false-GREEN; both-stamped duplicates → min wins. Scope name absent from manifest → AXIS-NULL (the subtraction the manifest-side iteration cannot see — CRITIC §1.2 direction, covered). Unicode: `.lower()` on BOTH sides (`activity.py` `from_groups`/`sections_for` + fold); a lower/casefold divergence (ß/STRASSE probe) refuses rather than mismatches silently. Uppercase scope (engine-contract violation) → refuses. Perf: 3.04 ms/fold over a 10,000-section manifest (50-run mean), pure CPU on an object already fetched — the OPT-7 zero-added-latency premise holds. |
| 4 | Concurrency / reuse | **PASS.** Manifest read result is a local in `execute_rows`; no state lands on the engine or module (`_ROWS_BASE_AXES`/`VERIFICATION_AXIS_FIELDS` are immutable tuples; `declare_axes` returns a fresh list; `axes_present` uses `default_factory`). `EntityQueryService()` constructed inside both handlers (`api/routes/query.py:468`, `:609`); the lifetime tripwire test drives TWO real route requests and asserts two distinct services each with an empty memo. Exception in the manifest read: `_read_serve_manifest` never raises → response **still serves** with `honest_contract_complete=False` (unchanged disposition) and the axis at AXIS-NULL (declared + null) → consumer REFUSES. That is exactly what TDD §5.3 rules (serve the response, refuse the axis, never 500, never silently dormant) — verified in code and by the engine-level tests on the absent and raise paths. |
| 5 | Canary honesty | **PASS.** `test_serve_verification.py` contains **zero** mock/patch usage — pure input fixtures. CAN-A is the CRITIC §5.1 binding construction verbatim: stamps PRESENT but OLD (the state a halted warmer actually produces — a halted warmer does not remove stamps), axis DERIVES, number crosses the bar; two-sided (same fixture at 600 s passes) plus the partial-halt min arm. It is not a synthetic large number: 7200 is `now − stamp` through the real fold. At producer scope this discharges clause (ii) as the critic ruled; the gate-level (ASR ABORT) half rides V3/SPR-V4 by design and is not claimed here. CAN-B (absent stamp + fresh `written_at` → null + backfill=true) plus the policy-divergence test (identical manifest to both callers) pin the G-2 refusal. **False-GREEN construction attempted and not found:** the only writer of `SectionInfo.last_verified_at` is the triple-gated stamp at `progressive.py:573` (the `cache/` hits are the documented unrelated `FreshnessStamp` subsystem); carry-forwards never freshen; the memo is per-request; the meta is computed per request even on a stale-served cache hit; the SEAM-1 dual-read fallback returns real-or-absent stamps, never synthesized ones. The two patch usages in the query-level suite are a raise-tripwire on `billable_sections`/`active_sections` (proves non-reachability — the request SUCCEEDS while they raise) and a fault-injection on the defensive catch (the M10 hole's cure); neither makes a canary pass. |
| 6 | The `manifest_read=` escape hatch | **PASS.** Exactly ONE production caller of `_derive_honest_contract_complete` exists (`engine.py:314`, inside `execute_rows`) and it threads `manifest_read` explicitly; the standalone arm (`engine.py:776`) is reachable only from callers that do not exist (grep over `src/`, `mcp/`, `scripts/`: none). The 5 pre-existing route tests (`test_routes_query_project_section_rows.py:254,300,344,394,444`) patch the derivation wholesale — they neither exercise nor guard the threading — but the load is carried by `TestOneManifestReadPerRequest` (`await_count == 1` asserted on success, absent, AND raise paths) and mutation M7 bites. The OPT-7 double-fetch hole is closed at the only site that matters. |
| 7 | Before-trace integrity | **RE-VERIFIED FIRST-HAND.** At 2026-08-19T17:18:32Z I issued the exact two consumer POSTs (same select list, `limit=1000`, `offset=0`, authenticated as the consumer's own service account) against the live producer: both 200, row counts 62/50 (matching the PR body's capture), **exactly the same sorted 20-key meta roster**, none of the three axis fields, no `axes_present`. AXIS-ABSENT confirmed live. See NOTE-1 for the image anchor caveat. |
| 8 | Suite / lint / types | **CONFIRMED, my own runs, in my worktree:** full unit suite `16603 passed, 29 skipped, 4 xfailed` (0 failures — see DEF-4 for the count delta vs the builder's 16592 and an xdist artifact); `worker_isolated` set `51 passed, 1 skipped`; `ruff format --check` 1458 files clean; `ruff check` clean; `mypy src/autom8_asana --strict` clean (598 files); `generate_openapi.py --check` up to date. New suites: 64/64. CLI equivalence pair: 104/104 with zero test edits (verified: PR diff touches no existing test file). |

**Mutation adequacy (anti-coverage-theater):** beyond re-running the suites, I
applied 4 mutations of my own, disjoint from the builder's M1–M14, each
apply→run→revert: QM-1 tolerate-one-missing-section (`missing > 1`) → 3 failed;
QM-4 drop the scope filter (fold whole manifest always) → 8 failed; QM-5
`verified_at` via `str()` (space-separated instant) → 4 failed; QM-7 drop
absent-section detection → 1 failed. Baseline restored green after each.
The suite bites on behavior, not lines.

**Merged-state check:** origin/main advanced to `8098d307` (#383,
intake-resolve — file-disjoint from this PR) during this wave. `git merge-tree`
clean; I built the real merge in my worktree and ran the verification suites +
#383's suite + the 5 patched route tests + the CLI equivalence pair on the
merged tree: **214 passed**. Worktree restored to the PR head afterward.

---

## §2 Defects (severity-ordered — none blocking)

**DEF-1 [LOW | TACTICAL] — `compute_serve_verification` docstring overclaims
"Never raises."** A naive-datetime stamp (or naive/aware mix) raises
`TypeError` inside the fold/subtraction (probed directly: `naive-stamp` and
`mixed-naive-aware` both RAISE). On the serve path this is SAFE — the engine's
broad-catch converts it to AXIS-NULL (declared + null → consumer refuses), and
`test_a_naive_manifest_stamp_never_reaches_the_wire` pins the end-to-end
outcome — but (a) the docstring lies to any future direct caller, and (b) the
naive-stamp refusal logs the generic `serve_verification_axis_derivation_failed`
(exc_info) instead of `serve_verification_axis_null` with a named reason, so
that arm is observable only as an exception log. Correction: fix the docstring;
optionally normalize/refuse naive stamps explicitly in the fold with a named
reason. Fold into V2/SPR-R1 housekeeping; not worth a re-spin of this PR.

**DEF-2 [LOW | TACTICAL] — whole-frame denominator counts entries, scoped
denominator counts names.** With `section_names=None` (whole-frame),
`in_scope = contributing + unstamped + null_named` counts manifest ENTRIES;
duplicate-named entries inflate the denominator, and (deliberately) null-named
entries force refusal. The scoped path counts unique NAMES. The divergence can
only over-refuse, never over-derive, and ASR never sends a whole-frame request
— but the two denominators will disagree in logs (`in_scope_count`) for the
same manifest. Document or unify when the whole-frame path gains a consumer.

**DEF-3 [INFO | STRUCTURAL] — explicit-section requests get the whole-frame
fold.** A rows request filtered by `section` selector (no classification)
resolves `classification_sections=None` → the axis folds over the entire
manifest, a SUPERSET of the response bytes. Direction is conservative
(min over a superset is ≤ the subset's min → the age can only read staler,
never fresher), so §1.4 CO-SOURCING is not violated in the dangerous
direction — but strictly, `verified_at` on such a response describes more
bytes than it accompanies. TDD §4.3 rules the whole-frame case for
no-classification requests generally; the section-selector sub-case is worth a
sentence in SPR-R1's roster. No ASR exposure (ASR always sends
classification).

**DEF-4 [INFO | environment] — builder's suite count is stale and xdist is
flaky here.** Head now collects 16603 (builder's body says 16592; the delta is
the coherence-pin commit `220829ec` adding tests after the body was written —
the direction is more tests, not fewer). Separately, my FIRST full-suite run
died in the xdist scheduler (`INTERNALERROR KeyError: <WorkerController gw4>`,
2 spurious fails, short collection); the clean rerun was 16603/0. Not
PR-related (the venv carries a stale-path shebang on `bin/mypy` too — the
environment has moved under this venv). If CI shows a one-off xdist internal
error on this PR, rerun before reading it as a defect.

---

## §3 Notes for the merge actor (the production act)

**NOTE-1 — the baseline image moved DURING this QA.** The PR body anchors the
before-trace to image `e3aab8d` (task-def `:787`). Valid at its 16:19Z capture
— but #383 merged and its auto-deploy was rolling at QA time (task-def `:788`,
image `8098d30`, `rolloutState: IN_PROGRESS` at 17:12:33Z; observed via ECS).
My 17:18Z re-pull (during that rollout) shows the meta roster UNCHANGED and the
axis still absent — #383 is intake-resolve-only — so the 20-key baseline holds
against current main. Consequences: (a) the merge lands on `8098d307`, not the
TDD's pin — clean merge, disjoint files, merged-state suites green; (b) the
UV-P-1 deploy-latency measurement at THIS merge must not confuse the tail of
the `:788` rollout with the SPR-V1 rollout — anchor on the task-definition
revision carrying the SPR-V1 image tag, not on "a deployment is in progress".

**NOTE-2 — exit criteria 7 and 8 remain merge-gated and unclaimed**, correctly:
live axis observation and deploy-latency measurement can only be discharged at
the merge. The re-verified before-trace above is their baseline.

**NOTE-3 — two worktree-guard WARNs were accepted during this QA** (QA worktrees
placed under the session scratchpad per dispatch, outside the blessed root);
both worktrees are removed at QA close, the `qa-v1` branch ref is left in the
repo for the merge actor.

---

## §4 Release recommendation

**GO-WITH-NOTES.** All ten V1 exit criteria that are pre-merge-dischargeable
are verified MET by my own hands; the two merge-gated criteria are correctly
unclaimed. The failure topology under every hostile input I could construct is
uniformly fail-safe (REFUSE/AXIS-NULL), never false-GREEN. DEF-1/DEF-2/DEF-3
are LOW/INFO and routed to SPR-R1-adjacent housekeeping, not to a re-spin.
NOTE-1 is operational and belongs to the merge actor. Handoff-relevant:
documentation impact NONE (additive wire fields, spec committed, OpenAPI
clean); security handoff NOT required (no auth/PII/crypto surface — service
auth untouched); SRE-relevant surface is the NOTE-1 deploy-anchor caution plus
the pre-existing `serve_verification_axis_null` observability obligation
(event named and shipped in this PR; the metric-filter binding is the sre
lane's, as the PR body states).

Acid test: if this goes to production and fails in a way I did not test, the
residual surprise lives in (a) the CodeArtifact-resolved SDK divergence class —
which is V2/V3's lane and PT-02's gate, not this leg's — and (b) real-S3
latency behavior of the threaded read, which is unchanged from the read
production already performs on every request.

*QA self-grade: MODERATE (same-rite, single attester; every load-bearing claim
above carries a first-hand receipt in this file's method notes).*
