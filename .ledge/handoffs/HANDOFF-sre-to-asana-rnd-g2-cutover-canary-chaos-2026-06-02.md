---
artifact_id: HANDOFF-sre-to-asana-rnd-2026-06-02
schema_version: "1.0"
source_rite: sre
target_rite: rnd
handoff_type: assessment
priority: high
blocking: true
initiative: g2-cutover-fallback-retirement-canary-chaos
created_at: "2026-06-02T16:30:00Z"
# HANDOFF schema (cross-rite-handoff, HANDOFF-009) mandates status: pending for an
# unaccepted handoff. The .ledge/ discoverability fields below are additive; they do
# NOT displace the schema-required status field.
status: pending
type: handoff
ledge_status: proposed
source_artifacts:
  - ".ledge/decisions/SRE-VERDICT-receiver-bulk-validation-2026-06-02.md"
  - ".know/obs.md"
  - "src/autom8_asana/cache/dataframe/build_coordinator.py"
  - "scripts/canary/receiver_bulk_fanout_deploy_gate.py"
  - "/Users/tomtenuta/Code/autom8/apis/asana_api/satellite/getdf_signals.py"
  - "/Users/tomtenuta/Code/autom8/terraform/observability_asana_dataframe_source.tf"
provenance:
  - { source: ".ledge/decisions/SRE-VERDICT-receiver-bulk-validation-2026-06-02.md", type: adr, grade: moderate }
  - { source: "src/autom8_asana/cache/dataframe/build_coordinator.py:131", type: code, grade: strong }
  - { source: "git show ab306f1e --stat (build_coordinator.py absent)", type: code, grade: strong }
evidence_grade: moderate
tradeoff_points:
  - attribute: "blast-radius safety"
    tradeoff: "prod width-gameday / prod ALERT-2a/2b firing / 7d composite window were NOT executed"
    rationale: "blast-radius bound forbids prod fault-injection; the live width-gameday against the deployed receiver is PROD-GATED. The deep validation here is a CODE+EVIDENCE adjudication plus chaos DESIGN, honestly flagged design-only."
items:
  - id: S7-001
    summary: "S7 fallback-retirement GO/NO-GO verdict = NO_GO. CONJUNCT-2 REFUTED (CF-1 structurally unchanged by #92), CONJUNCT-3 NOT CLOSED, CONJUNCT-4 UNPROVEN; no landed post-#92 re-gate evidence."
    priority: critical
    assessment_questions:
      - "Implement R1 (raise uvicorn worker count and/or tune max_concurrent_builds semaphore at build_coordinator.py:131) sized against measured saturation at 104-project width — does it lift the throughput ceiling that falsified #90?"
      - "Once R1 lands, execute the PROD width-gameday (DESIGN-ONLY here) to produce the >=99%-under-representative-width measurement the gate requires, and land a post-#92 re-gate verdict in .ledge/decisions/."
      - "Resolve the SECTION-ARM CONTENT-CONTRACT BLIND SPOT: confirm office_phone/vertical are genuinely out-of-schema for section frames (scope S7 Project-only for the column dimension) OR add a section-appropriate content assertion."
  - id: S7-002
    summary: "LIVENESS-MASQUERADE survives: the deploy-gate canary and the receiver success metric are both 2xx-shaped and read no content/EMF/column signal. The canary->content binding is MISSING."
    priority: high
    assessment_questions:
      - "Bind a live canary assertion to Contract-B column CONTENT (read the TD-007 honest receiver EMF, or assert office_phone/vertical/gid presence in the returned frame) so a 2xx carrying an empty/wrong frame fails the gate."
---

# HANDOFF — SRE → autom8y-asana rnd (+ legacy monolith): G2-Cutover Canary + Chaos + S7 GO/NO-GO

> **Recipients**: the autom8y-asana rnd thread + the legacy monolith (`/Users/tomtenuta/Code/autom8`).
> **Handoff type**: assessment (validation + assessment). **Blocking**: yes — consumer cutover stays BLOCKED.
> **S7 verdict**: **NO_GO** (not NO_GO_PENDING_WINDOW — see §3, §4).
> **Discipline**: default-to-refuted; every shipped/landed/verified claim carries a `file:line` anchor or an explicit `[UNATTESTED — DEFER]` tag. NO prod fault-injection was executed; prod items are flagged DESIGN-ONLY.

---

## §1. The FUNCTIONAL canary signal contract (acid-tested, file:line cited) — from P0

The G2 functional contract is SIG-1..SIG-6, emitted at the monolith `Project.get_df` / `Section.get_df` chokepoints, CloudWatch EMF, namespace `Autom8y/AsanaDataframeSource` (`getdf_signals.py:70`). The acid test on every signal: *"could a container short-circuiting at the entry handler, never invoking get_df, satisfy this signal? YES = reject."*

| Signal | What it asserts | file:line anchor | Acid test |
|--------|-----------------|------------------|-----------|
| **SIG-1** | per-project path discrimination (satellite \| fallback), split-by-arm; carries SIG-6 flag echo | `getdf_signals.py:8`, emit at `getdf_signals.py:243-256` | **PASS** — emitted INSIDE get_df; a short-circuit emits nothing, and the SLI metric is dense-by-construction so a missing-emit day reads as breaching (`terraform:250`). |
| **SIG-2** | T2.FALLBACK fire event (reason) | `getdf_signals.py:9`; section fallback emit at `section/main.py:712` | **PASS** — fires on the fallback arm before the legacy attempt; not fakeable by entry short-circuit. |
| **SIG-3** | column-contract assertion (office_phone + vertical + gid PRESENCE) — the offer_holders join contract [ALERT-2a defeat] | gate `if assert_column_contract:` at `getdf_signals.py:277`; `_CONTRACT_COLUMNS = ("office_phone","vertical","gid")` at `getdf_signals.py:77` | **PASS for content** — asserts presence on a REAL frame; a short-circuit cannot produce the frame. **BUT PROJECT-ARM ONLY** — see §6 blind spot. |
| **SIG-4** | satellite row-count floor + honest-contract presence [ALERT-2b / SCAR-029 defeat]; honest-contract attr stamped only on non-empty frames | `getdf_signals.py:11`; row-count + honest-present emit at `getdf_signals.py:298-312`; stamp at `_bridge.py:136-137` (`if not df.empty: df.attrs[HONEST_CONTRACT_FLAG]`) | **PASS** — real-frame-bound; row_count==0 on a known-populated project is the trip. |
| **SIG-5** | refresh-run roll-up derived from SIG-1/SIG-2 EVENTS (not return tuples) | `getdf_signals.py:12`, accumulator feed at `getdf_signals.py:317` | **PASS** — event-sourced, not return-value-sourced. |
| **SIG-6** | flag-state echo `SATELLITE_GET_DF_ENABLED` (rollback observable) | `getdf_signals.py:13`; echo field at `getdf_signals.py:256`; section flag read at `section/main.py:671` | **PASS** — rollback is observable via the echoed flag. |

**Contract-B (column content)**: `_CONTRACT_COLUMNS = ("office_phone","vertical","gid")` (`getdf_signals.py:77`). The consumer that makes office_phone/vertical load-bearing is `offer_holders/main.py:56` (`get_df(...)[["office_phone","vertical"]]`), with the silent-vanish risk at the empty-pairs source (`offer_holders/main.py:41,60`). SIG-3 is the structural defeat of that silent vanish — **on the Project arm only**.

---

## §2. Chaos verdicts — executed-vs-design delineation — from P2

| Chaos probe | Target conjunct | Status | Delineation |
|-------------|-----------------|--------|-------------|
| Build-concurrency saturation under representative multi-project WIDTH (104 projects) | CONJUNCT-2 (CF-1 PRIMARY) | **EXECUTED at #90** (gameday) → **FAIL**: rate collapsed below the 82% high-water mark (`SRE-VERDICT...:37,50`). **NOT re-executed post-#92** (PROD-GATED). | The #90 gameday is the only executed width-chaos. No post-#92 width re-run exists. |
| Task-restart-mid-build orphan (CF-2) | CONJUNCT-3 | **OBSERVED at #90** (`build_coordinator_initialized` 09:20:18 + ELB-502s 09:19-20, `obs.md:100`). Drain (TD-004) **NOT chaos-verified under live restart** (PROD-GATED). | Drain code shipped (§3); its restart-mid-build proof is **DESIGN-ONLY**. |
| Singleflight coalescing under concurrent same-key load | CONJUNCT-4 | **NEVER EXERCISED** — #90 produced only 2 distinct-key builds for one gid, zero `coalesced` events (`obs.md:102`). The R4/R5 proofs are **DESIGN-ONLY** (PROD-GATED). | No live coalesced-count>0 receipt exists. |
| 503 `Retry-After` live-firing under bulk (R5) | CONJUNCT-4 | Header **structurally wired** at `errors.py:621-627` (conditional on `exc.details["retry_after_seconds"]`); **live-firing UNPROVEN** (PROD-GATED). | Code present, live receipt absent. |

**Executed**: the #90 width-gameday (FAIL) + the CF-2 orphan observation. **Design-only (PROD-GATED, NO prod run executed per blast-radius bound)**: every post-#92 re-validation — width-gameday, drain-under-restart, singleflight-coalescing, 503-Retry-After-live, prod ALERT-2a/2b firing, the 7d composite window.

The existing deploy-gate canary (`receiver_bulk_fanout_deploy_gate.py`) can only smoke locally against `localhost:5300` if a substrate exists; **no local or prod canary run was executed for this handoff** — do not read any green liveness check as a width-gameday pass.

---

## §3. The S7 GO/NO-GO verdict — necessary + sufficient evidence chain — from P3

**The gate (the #90 FAIL verdict, default-to-refuted):** S7 clears iff ALL of —
(1) cred representative **AND** (2) measured >=99% under realistic bulk **AND** (3) residual 5xx root-caused **AND CLOSED** **AND** (4) singleflight / Retry-After / SA-isolation **PROVEN under live load**.
At #90: **1-of-4 MET** (`SRE-VERDICT...:41`). (1) MET; (2) NOT MET (82% high-water, collapsed below under chaos); (3) NOT MET (root-caused to ECS task restart mid-build, failure mode OPEN); (4) UNPROVEN.

**#92 is the fix under test** (HEAD `ab306f1e`). The adjudication question: does #92 move conjuncts (2)(3)(4) from REFUTED toward MET under the SAME representative width that falsified #90?

**Necessary+sufficient evidence chain → verdict:**

1. **CONJUNCT-2 is the load-bearing necessary condition** (a measured >=99% under representative width). It is **REFUTED** because the CF-1 PRIMARY contributing factor (build concurrency starvation) is **structurally UNCHANGED by #92** — `build_coordinator.py` is absent from the #92 diff (`git show ab306f1e --stat`), `max_concurrent_builds: int = 4` stands at `build_coordinator.py:131`, single uvicorn worker stands (`lifespan.py:233`), and **R1 (the named CF-1 fix) was not implemented**. See §5.
2. **No landed re-gate evidence exists** — the >=99%-under-width measurement the gate requires has not been produced; the only path to it is a PROD width-gameday that was not executed here.
3. **CONJUNCT-3 is NOT closed; CONJUNCT-4 is UNPROVEN** (§5).
4. Therefore the gate remains at **1-of-4 MET**. **Sufficient condition for GO is not met. Verdict: NO_GO.**

The S7 composite gate that authorizes Stage-B fallback deletion requires OK-continuous 7-of-7 daily >=99% on **BOTH** Project AND Section arms — `g2_satellite_success_sli_7d_gate`, `alarm_rule = join(" OR ", [ALARM(project), ALARM(section)])` at `terraform:301-309`; per-chokepoint, dense-by-construction `for_each = toset(["project","section"])` at `terraform:247`. No clock can start while conjunct 2 is unmet.

---

## §4. HONEST design-vs-executed delineation

| Item | Status | Anchor / flag |
|------|--------|---------------|
| Code+evidence adjudication of #92 vs the #90 gate | **EXECUTED** (this handoff) | front-door reads in §1, §3, §5 |
| #90 width-gameday FAIL + CF-2 orphan observation | **EXECUTED at #90** | `SRE-VERDICT...:37,50`; `obs.md:100` |
| PROD width-gameday at representative width (post-#92) | **DESIGN-ONLY** — `[UNATTESTED — DEFER]` (PROD-GATED; no prod run executed) | blast-radius bound |
| PROD ALERT-2a (column-contract) firing | **DESIGN-ONLY** — `[UNATTESTED — DEFER]` | `terraform:180-185` (composite present, not fired) |
| PROD ALERT-2b (empty-frame) firing | **DESIGN-ONLY** — `[UNATTESTED — DEFER]` | ALERT-2 composite `terraform:180` |
| 7d composite SLI window (Project AND Section >=99%) | **DESIGN-ONLY — WINDOW NOT STARTED** — `[UNATTESTED — DEFER]` | `terraform:301-309` |
| Drain-under-live-restart, singleflight-coalescing, 503-Retry-After-live | **DESIGN-ONLY** — `[UNATTESTED — DEFER]` | §2 |

The 7d composite window is **not the sole gap** (which would warrant NO_GO_PENDING_WINDOW). It sits atop **2 refuted + 1 unproven** conjuncts. Verdict is **NO_GO**, not NO_GO_PENDING_WINDOW.

---

## §5. Adversarial BLOCKING findings (the gate S7 must clear)

### B1 — CONJUNCT-2 REFUTED — CF-1 PRIMARY is structurally UNCHANGED by #92
Build concurrency starvation under width is unchanged: `max_concurrent_builds: int = 4` (`build_coordinator.py:131`) + single uvicorn worker (`lifespan.py:233` — "single-worker uvicorn" comment at the `BuildCoordinator` init). `build_coordinator.py` is **NOT in the #92 diff** (`git show ab306f1e --stat` — the 25 changed files do not include it; verified). **R1** (the named CF-1 fix: raise worker count / tune the build semaphore, `SRE-VERDICT...:131`, owner Platform Engineer) was **NOT implemented**. #92 addressed CPU-on-loop starvation (TD-001, `dataframes/concurrency.py`), drain (TD-004, `lifespan.py:34`), observability (TD-007, `api/metrics.py`), warmer (TD-005, `cache/dataframe/warmer.py`), LKG honesty (TD-006, `settings.py` default flip) — **none raises the throughput ceiling** that falsified #90 at representative width.

### B2 — NO LANDED RE-GATE EVIDENCE
`obs.md` RECV-BULK-001/002/003 are all still "Open at 2026-06-02" (`obs.md:98,100,102`); there is **no post-#92 measured bulk re-run verdict** in `.ledge/decisions/` (the only bulk-validation verdict present is the #90 FAIL, `SRE-VERDICT-receiver-bulk-validation-2026-06-02.md`; verified by directory listing). The >=99% measurement under representative multi-project WIDTH that the gate requires has not been produced. The only path to it is a PROD width-gameday — **PROD-GATED = DESIGN-ONLY here; no prod run executed** per the blast-radius bound.

### B3 — CONJUNCT-3 NOT CLOSED
TD-004 drain (`lifespan.py:_drain_background_builds` at `lifespan.py:34`; `settings.py:733` Field, default `25.0` at `settings.py:734`) mitigates CF-2, but its load-bearing safety invariant (`drain_timeout <= ECS deregistration_delay`) is **explicitly NOT enforced in code** ("deregistration_delay is an infra (TF) config and is NOT enforced in code here", `settings.py:732`). RECV-BULK-002 still Open (`obs.md:100`); drain is **UNPROVEN under live restart-mid-build**.

### B4 — CONJUNCT-4 UNPROVEN
Singleflight coalescing (coalesce path at `build_coordinator.py:184-191`, `builds_coalesced` stat at `build_coordinator.py:190`; the SRE-VERDICT/obs cite the path at `build_coordinator.py:194`), 503 `Retry-After` (`errors.py:621-627`), and SA-isolation have **no live receipt**; RECV-BULK-003 still Open (`obs.md:102`). The R4/R5 chaos proofs are PROD-gated = DESIGN-ONLY here.

### B5 — LIVENESS-MASQUERADE SURVIVES
The deploy-gate canary is **HTTP-status-only**: `success` inferred from `200 <= status < 300` at `receiver_bulk_fanout_deploy_gate.py:404`, with the `successes: int = 0  # 2xx` field at `:102` and `success_rate = successes / (successes + server_errors)` at `:108-118`. It reads **NO content/EMF/column signal**. The receiver-side `receiver_query_success_rate` metric is also 2xx-shaped (`record_receiver_query_outcome`: "success: True on 2xx; False on 5xx" at `api/metrics.py:241`; `success_rate = 2xx / (2xx + 5xx)` at `api/metrics.py:346`). A 2xx carrying an empty/wrong frame counts as success in BOTH. **Acid test FAILS**: a container short-circuiting at the entry handler, never invoking get_df, satisfies both signals. The canary→content binding (a live emit asserting Contract-B column CONTENT) is **MISSING** — the TD-007 honest signals (`serving_stale_total` at `api/metrics.py:290`; `success_rate_with_stale_context` at `api/metrics.py:388`) are receiver-side EMF the canary does not read.

### B6 — SECTION-ARM CONTENT-CONTRACT BLIND SPOT (from P0)
SIG-3 office_phone/vertical/gid PRESENCE is **PROJECT-arm only**: the gate `if assert_column_contract:` (`getdf_signals.py:277`) defaults `assert_column_contract: bool = True` (`getdf_signals.py:220`), but the Section caller passes `assert_column_contract=False` (`section/main.py:767`). The S7 composite retires **BOTH** arms (`terraform:301-309`, OR over project AND section). The Section half has **ZERO office_phone/vertical content coverage** (only `gid` is a receiver invariant — `getdf_signals.py:235-238` rationale). Gates S7 unless **(a)** office_phone/vertical are confirmed genuinely out-of-schema for section frames → scope S7 Project-only for the column dimension, OR **(b)** a section-appropriate content assertion is added.

### B7 — 7d COMPOSITE WINDOW NOT STARTED
`terraform:301-309` requires OK-continuous 7-of-7 daily >=99% on **BOTH** Project AND Section arms; no clock can start while conjunct 2 is unmet and no >=99% measurement has landed. The window is **not the SOLE gap** (which would warrant NO_GO_PENDING_WINDOW); it sits atop 2 refuted + 1 unproven conjuncts, so the verdict is **NO_GO**, not NO_GO_PENDING_WINDOW. **FALLBACK RETAINED** (`section/main.py:632` legacy-SDK boundary, `SatelliteClientError`/`TokenAcquisitionError` → legacy SDK at `section/main.py:642-643`); **consumer cutover stays BLOCKED**.

---

## §6. Routing — what each recipient owns next

**To autom8y-asana rnd (receiver-side, the path to GO):**
- **R1 (Platform Engineer)** — raise uvicorn worker count and/or tune `max_concurrent_builds` (`build_coordinator.py:131`) against MEASURED saturation at 104-project width, not a guess. This is the necessary unblock for CONJUNCT-2. [B1]
- **R2/R3 (Platform Engineer)** — close CONJUNCT-3: prove drain holds under live restart-mid-build; enforce or assert the `drain_timeout <= deregistration_delay` invariant (currently NOT enforced, `settings.py:732`). [B3]
- **R4/R5 (Chaos Engineer)** — once R1 lands, execute the PROD width-gameday (DESIGN-ONLY here) to produce the >=99% measurement; prove singleflight coalescing (`coalesced` count > 0 + one `completed`) and live 503 `Retry-After`. Land a post-#92 re-gate verdict in `.ledge/decisions/`. [B2, B4]
- **Canary fix** — bind a live canary assertion to Contract-B column CONTENT (read TD-007 honest EMF or assert column presence on the returned frame), defeating the LIVENESS-MASQUERADE. [B5]

**To the legacy monolith (`/Users/tomtenuta/Code/autom8`):**
- Resolve the SECTION-ARM blind spot: confirm office_phone/vertical out-of-schema for section frames → scope S7 Project-only for the column dimension (`section/main.py:767`), OR add a section-appropriate content assertion. [B6]
- **DO NOT** delete the section legacy-SDK fallback (`section/main.py:632`) — fallback RETAINED until S7 clears. [B7]

---

## §7. Verdict line

**S7 fallback-retirement: NO_GO.** Gate remains at 1-of-4 conjuncts met (`SRE-VERDICT...:41`). CONJUNCT-2 REFUTED (CF-1 structurally unchanged by #92), CONJUNCT-3 NOT CLOSED, CONJUNCT-4 UNPROVEN, no landed re-gate evidence, LIVENESS-MASQUERADE survives, section-arm content-contract blind spot open, 7d window not started. Consumer cutover stays BLOCKED; legacy-SDK fallback RETAINED.

*Prepared by SRE / Incident Commander, 2026-06-02. Default-to-refuted held throughout. All prod fault-injection items flagged DESIGN-ONLY per blast-radius bound; no prod run was executed.*
