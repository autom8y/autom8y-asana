---
artifact_id: SCOUT-asana-r2-r3-disposition
type: spike
schema_version: "1.0"
rite: rnd
agent: technology-scout
created_at: "2026-06-02"
initiative: g2-cutover-fallback-retirement-canary-chaos
source_handoff: ".ledge/handoffs/HANDOFF-sre-to-asana-rnd-g2-cutover-canary-chaos-2026-06-02.md"
status: proposed
evidence_grade: moderate
self_cap: MODERATE
classification_scope: "R2 (canary->content binding), R3 (S7 column-contract gate re-scope)"
---

# SCOUT — asana R2 / R3 disposition (RND_NOW vs DEFER_10X)

> **Lens**: This is a build-vs-defer triage, not a technology adoption scan. The
> "technology" under evaluation is two named remediation builds carried by the SRE
> tribute handoff. Each is classified RND_NOW (build in the rnd/10x-dev arming wave
> now) or DEFER_10X (watch-gated, hand to 10x-dev later). Every load-bearing premise
> is front-door verified with a `{path}:{line}` anchor; no premise is propagated from
> the handoff without independent inspection.
>
> **Acid test applied to each item**: *"If we don't build this now, does the S7
> fallback-retirement gate produce a FALSE-GREEN — i.e. authorize deleting the
> legacy-SDK net while the satellite path is silently broken?"* A YES forces RND_NOW
> (the item is a gate-validity defect, not an enhancement). A NO permits DEFER_10X
> with a bound watch-trigger.

---

## §0. Premise verification ledger (front-door, independent of the handoff)

| # | Premise (from handoff) | Verified at | Verdict |
|---|------------------------|-------------|---------|
| P1 | The deploy-gate canary decides success from HTTP 2xx only; reads no content/EMF | `scripts/canary/receiver_bulk_fanout_deploy_gate.py:399` (`if 200 <= status < 300: results.successes += 1`), `:109-119` (`success_rate = successes / (successes + server_errors)`) | **CONFIRMED** — the only per-call classifier is `status_code`; the response BODY is never parsed (`_one_call` at `:341-372` returns `(status, ms)`, discards `resp.json()`). |
| P2 | The receiver-side success metric is also 2xx-shaped (no content read) | `src/autom8_asana/api/metrics.py:231` (`record_receiver_query_outcome(entity_type, success)`), `:344` (`receiver_query_success_rate`) | **CONFIRMED** — `success: bool` is the only input; no column assertion. |
| P3 | SIG-3 (column-contract office_phone/vertical/gid) + SIG-4 (row-floor) are the functional content contract | `/Users/tomtenuta/Code/autom8/apis/asana_api/satellite/getdf_signals.py:277-296` (SIG-3), `:300-315` (SIG-4); `_CONTRACT_COLUMNS = ("office_phone","vertical","gid")` at `:77` | **CONFIRMED** — content assertion is real-frame-bound. |
| P4 | SIG-3/SIG-4 are emitted **only in the legacy monolith**, NOT at the autom8y-asana receiver | EMF emit lives at `/Users/tomtenuta/Code/autom8/apis/asana_api/satellite/getdf_signals.py` (monolith path); receiver `src/autom8_asana/api/metrics.py` has NO `office_phone`/`vertical`/`ColumnContractFailure` emit (grep-confirmed: only `serving_stale_total` `:289`, `success_rate_with_stale_context` `:388`) | **CONFIRMED + LOAD-BEARING for R2 effort** — the content signal the canary must bind to does not exist receiver-side as an EMF the canary can read; the canary would have to assert column presence on its OWN returned frame. See §1. |
| P5 | The S7 composite gate ORs over BOTH project AND section arms | `/Users/tomtenuta/Code/autom8/terraform/observability_asana_dataframe_source.tf:306-309` (`alarm_rule = join(" OR ", [ALARM(...project...), ALARM(...section...)])`); `for_each = toset(["project","section"])` at `:247` | **CONFIRMED** — both arms are gate members. |
| P6 | The Section arm passes `assert_column_contract=False` **by design** (section frames legitimately lack office_phone/vertical) | `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/section/main.py:767` (`assert_column_contract=False`), inline rationale at `:758` ("SIG-3 column-contract is SKIPPED (project-only contract)"); contract semantics at `getdf_signals.py:233-241` ("Section frames are guaranteed gid ... but legitimately carry NO office_phone/vertical") | **CONFIRMED** — the Section column-contract is genuinely out-of-schema, not a bug. |

All six premises hold under independent inspection. No premise was found false or partial. The handoff's `file:line` anchors are accurate (spot-checked: `getdf_signals.py:277`, `section/main.py:767`, `terraform:301-309`, canary `:404` ≈ `:399` 2xx classifier — handoff cited `:404`, actual classifier is `:399`; the `success` field comment is at `:102` as cited; off-by-five is the only drift, non-material).

---

## §1. R2 — bind the canary to Contract-B CONTENT — **RND_NOW**

### Statement
Replace the HTTP-2xx liveness-masquerade in `receiver_bulk_fanout_deploy_gate.py`
with a content assertion that reads Contract-B columns (office_phone/vertical/gid
presence + non-empty frame) so a 2xx carrying an empty or wrong frame FAILS the gate.

### Acid test → **YES, gate produces FALSE-GREEN without it**
The canary's `success_rate` (`:109-119`) and the receiver's `receiver_query_success_rate`
(`api/metrics.py:344`) are BOTH `2xx/(2xx+5xx)`. A container that short-circuits at the
entry handler — never invoking get_df, returning a 200 with `[]` — scores as success in
both signals. This is the exact SCAR-029 silent-vanish fingerprint the whole G2 observability
seed was built to defeat (`terraform:164` ALERT-2b rationale: "the active ad set silently
vanishes downstream"). A canary that cannot see this is not a functional canary; it is a
liveness check mislabeled as a deploy gate. The deploy-gate decision (`_evaluate_gate` at
`:432-459`) would authorize promotion on a silently-broken satellite. **This is a gate-validity
defect, not an enhancement.**

### Why RND_NOW (not DEFER_10X)
1. **It is on the critical path to the ONLY thing S7 GO needs.** The handoff's verdict
   chain (§3) makes a measured `>=99%-under-representative-width` the load-bearing necessary
   condition. That measurement is meaningless if "success" is 2xx-shaped — a 99% 2xx rate on
   empty frames is a false pass. R2 is a *precondition for the validity of the R1 width-gameday
   measurement*, not a parallel nice-to-have. Building R1's measurement on a 2xx canary would
   manufacture exactly the over-projected-PASS error this campaign's discipline refuses.
2. **Low blast-radius, no prod fault-injection.** R2 is a read-path assertion change in a
   probe script (`scripts/canary/`), not a receiver-code or terraform-apply change. It can be
   built and unit-tested against a deliberately-broken fixture (a 200+empty-frame stub) entirely
   off-prod. It does NOT trip the blast-radius bound that gates R1/R4/R5 (those need a live
   width-gameday).
3. **Composable-simplicity fit** [AD:SRC-005 Anthropic 2024] [MODERATE | 0.72 @ 2026-03-31]:
   the change is the smallest possible — parse `resp.json()` (already discarded at `:363`),
   assert `{"office_phone","vertical","gid"} <= set(columns)` and `row_count > 0`, fold into
   the per-arm classifier at `:399`. No new framework, no orchestration.

### Non-obvious build constraint (the P4 finding — hand to integration-researcher)
The content contract the canary must assert (SIG-3/SIG-4 columns) is emitted as EMF **only in
the legacy monolith** (`getdf_signals.py`), NOT at the autom8y-asana receiver
(`api/metrics.py` has no `ColumnContractFailure`/`office_phone` emit — P4). Two viable bind-targets,
in preference order:
- **(a) PREFERRED — assert on the canary's OWN returned frame.** The canary already issues
  `POST /v1/query/{arm}/rows` (`:349`) and receives the row payload; it discards the body at
  `:363`. Bind by parsing that body and asserting Contract-B column presence + non-empty —
  a *direct content read*, no dependency on receiver-side EMF. This is the acid-test-passing
  bind (a short-circuit cannot produce the columns).
- **(b) FALLBACK — read TD-007 honest EMF.** `serving_stale_total` (`api/metrics.py:289`) +
  `success_rate_with_stale_context` (`:388`) exist receiver-side, but they are a STALENESS
  honesty signal, NOT a column-content contract. Binding to (b) alone would NOT defeat the
  column-vanish (an LKG-honest 200 can still drop office_phone). **(b) is insufficient on its
  own; (a) is the load-bearing bind.** This corrects a possible misread of the handoff's "read
  TD-007 honest EMF" suggestion — TD-007 covers stale-context honesty, not column content.

### Scope boundary (Project vs Section content)
The `/v1/query/section/rows` arm (`:490`) returns section frames that legitimately lack
office_phone/vertical (P6). The R2 content assertion MUST be arm-aware: assert the full
office_phone+vertical+gid contract on the **project** arm only; assert gid-presence + non-empty
on the **section** arm. Folding a project-grade column assertion onto the section arm would
manufacture false canary failures — the mirror-image of the R3 defect. (This couples R2 to R3;
see §3.)

### Disposition
**RND_NOW.** Route to integration-researcher (bind-target dependency map: option (a) frame-content
read vs (b) receiver EMF; arm-aware assertion scoping) then prototype-engineer (deliberately-broken
200+empty fixture per `canary-signal-contract` discipline). This is the canary→content binding the
handoff §6 names; it is a precondition for the validity of the R1 width measurement, so it leads
the arming wave.

---

## §2. R3 — re-scope the S7 column-contract gate Project-only — **RND_NOW**

### Statement
The S7 column-contract dimension must be scoped Project-only. Section frames pass
`assert_column_contract=False` by design (P6), so the Section arm emits NO `ColumnContractFailure`
metric — yet the gate's narrative + dashboard treat the column dimension as covering both arms.

### Acid test → **YES, latent gate-definition defect with two failure modes**
There are two distinct sub-claims; I verified the actual gate wiring to separate the real defect
from a phantom one:

- **The 7d SUCCESS-RATIO composite (`g2_satellite_success_sli_7d_gate`, `terraform:301-309`) is
  NOT column-contract-scoped.** It ORs the per-source *satellite-success-ratio* alarms
  (`GetDfSatellite/(GetDfSatellite+GetDfFallback)`, `:263-296`), which are emitted on EVERY call
  on BOTH arms (SIG-1, dense-by-construction, `:247-250`). So the **ratio** gate does NOT wait
  forever on a missing Section signal — the memory note's "wait forever" framing applies to the
  *column-contract* dimension, not the success-ratio composite. **This distinction is load-bearing:
  the success-ratio gate is correctly per-chokepoint; only the column-contract dimension is
  mis-scoped.** [Corrects a possible over-broad reading of the handoff B6/B7.]

- **The ALERT-2 column-contract composite (`g2_silent_functional_failure`, `terraform:180-199`)
  is the BUNDLE member that gates S7 on content** (gate-bundle requirement stated at
  `terraform:241-243`: "the ALERT-2 composite ... must ALSO be GREEN"). Its `ColumnContractFailure`
  member (`:143-159`) is `{Path=satellite}`-pinned and, per the dashboard P3 comment at
  `terraform:399`, is **"Project-pure post-CR3-S1 (sections pass assert_column_contract=False, so
  they emit no SIG-3)."** So the metric is ALREADY structurally Project-only at the emit layer
  (P6) — **but the gate's S7 narrative + the operator-facing dashboard guide do NOT say so.** The
  defect is a **documentation/scope-declaration gap**, not a forever-blocking alarm: the alarm uses
  `treat_missing_data = "notBreaching"` (`:154`), so a section-absent column signal does NOT block.

### Why this is still RND_NOW (despite being narrower than first framed)
The defect is real and S7-gate-affecting, just not the "wait forever" failure mode:
1. **Operator-facing scope ambiguity authorizes a wrong decision.** The S7 gate narrative
   (`terraform:206-243`) and the dashboard reading-guide (`:337`) tell the operator the column
   dimension covers the cutover of BOTH fallbacks (OD-3). An operator reading the green column-contract
   alarm as "both arms' content is verified" would be FALSE-ASSURED — the Section arm's content is
   NEVER asserted (by design). When S7 authorizes deleting the **Section** legacy-SDK fallback
   (`section/main.py:632`, per handoff B7), the operator must know the Section content contract was
   *intentionally never gated* — otherwise the gate over-claims. This is a telos-integrity /
   gate-honesty defect: the gate must declare what it does NOT cover.
2. **It couples to R2.** R2's arm-aware content assertion (§1 scope boundary) and R3's
   gate-scope declaration are the SAME boundary stated at two altitudes (canary probe + terraform
   gate narrative). Building R2 without R3 leaves the terraform gate over-claiming; building R3
   without R2 leaves the live canary blind. They are one coherent change to the Project-vs-Section
   content-contract boundary and should land together.
3. **Near-zero blast-radius.** R3 is a terraform *narrative/scope-declaration* edit (alarm
   descriptions + dashboard guide text + an explicit "column-contract dimension is Project-only;
   Section content is intentionally un-gated — gid is the shared receiver invariant" note). It is
   NOT a logic change to the alarm rules (the success-ratio composite stays per-chokepoint; the
   column alarm stays notBreaching+Project-pure). No prod-apply behavior change to the breaching
   gate; pure honesty/scope-declaration hardening.

### Disposition
**RND_NOW.** Route to integration-researcher to confirm the gate-narrative edit surface (which
alarm descriptions + dashboard text assert the column dimension), then a small terraform doc/scope
change. Land coupled with R2 as one Project-vs-Section content-contract boundary change. The
`gid` shared receiver invariant (`getdf_signals.py:235-241`) is the one content signal that IS
valid on both arms and may remain a both-arm content assertion.

---

## §3. Coupling, sequencing, and comparison matrix

R2 and R3 are the **same boundary at two altitudes** (live canary probe + terraform gate
narrative). They share one premise (P6, the Project-only column contract) and one design decision
(arm-aware content scoping). Building either alone leaves a half-closed boundary. Recommend they
land as one coupled arming-wave change.

### Decision matrix

| Option | Closes liveness-masquerade (B5) | Closes gate-scope over-claim (B6) | Blast-radius | Prod fault-injection | Acid-test (false-green risk) |
|--------|---------------------------------|-----------------------------------|--------------|----------------------|------------------------------|
| **Status quo (defer both)** | NO — 2xx-empty passes | NO — gate over-claims section content | n/a | none | **FAIL** — both false-green vectors stay open |
| Build R2 only | YES (canary) | NO (terraform still over-claims) | low | none | PARTIAL — canary honest, gate narrative still lies |
| Build R3 only | NO (canary still blind) | YES (gate declares scope) | near-zero | none | PARTIAL — gate honest, live probe still blind |
| **Build R2 + R3 coupled (RECOMMENDED)** | **YES** | **YES** | low | none | **PASS** — both vectors closed at both altitudes |

Status quo is the disqualified baseline: it is exactly the SCAR-029 silent-vanish the entire
G2 observability seed exists to defeat. R2+R3 coupled is the only option that closes both
false-green vectors. Neither requires prod fault-injection, so neither is blocked by the
blast-radius bound that gates R1/R4/R5 (the width-gameday family). **R2+R3 can proceed in the
arming wave immediately and in parallel with R1.**

### Sequencing within the arming wave
- **R2 + R3 (this disposition): RND_NOW, parallel-with-R1, off-prod.** They make the
  forthcoming R1 width-gameday measurement *valid* (a 2xx-only measurement is a false pass).
- **R1 (worker concurrency, `build_coordinator.py:131`): RND_NOW but separate** — owned by
  platform-engineer; it is the throughput-ceiling fix, out of scope for this R2/R3 disposition
  but the necessary CONJUNCT-2 unblock.
- **R4/R5 (width-gameday, singleflight, 503-Retry-After): PROD-GATED** — design-only until R1
  lands; not this disposition's scope.

---

## §4. Verdict line

- **R2 (canary→Contract-B content binding): RND_NOW.** Gate-validity defect; precondition for the
  validity of the R1 width measurement; low blast-radius, no prod fault-injection. Bind to the
  canary's own returned frame (option (a)), arm-aware (project: office_phone+vertical+gid; section:
  gid+non-empty). TD-007 honest EMF (option (b)) is staleness-honesty, NOT column content — insufficient alone.
- **R3 (S7 column-contract gate Project-only re-scope): RND_NOW.** Latent gate-scope over-claim
  (narrower than "wait forever" — the success-ratio composite is already per-chokepoint; only the
  column-contract dimension narrative over-claims). Near-zero blast-radius terraform narrative/scope
  edit; couples to R2; land together.

**Neither item is DEFER_10X.** Both are gate-honesty defects on the S7 fallback-retirement path
whose acid test returns YES (status quo produces a FALSE-GREEN authorizing deletion of the
legacy-SDK net while the satellite path is silently broken). No defer-watch-manifest entry is
warranted; deferring either would perpetuate the SCAR-029 silent-vanish the campaign exists to
close.

### Handoff readiness (rnd → integration-researcher)
- [x] Both items researched; all six load-bearing premises front-door verified with `{path}:{line}` anchors (§0)
- [x] Acid test applied per item; FALSE-GREEN risk is the discriminator
- [x] Build-vs-defer matrix includes status quo baseline (§3)
- [x] Non-obvious build constraint surfaced (P4: SIG-3/SIG-4 are monolith-only; canary must read its own frame)
- [x] Coupling + sequencing vs R1/R4/R5 stated
- [x] Clear verdict: R2 RND_NOW, R3 RND_NOW, coupled

**Evidence grade: MODERATE** (self-ref ceiling per `self-ref-evidence-grade-rule`; single-rite
authorship of a build-triage on the authoring fleet's own gate). Front-door verification of all
six premises raises confidence within the MODERATE band but does not lift the ceiling.

*Prepared by rnd / technology-scout, 2026-06-02. Default-to-refuted held: each handoff premise was
independently re-inspected before propagation; the "wait forever" and "TD-007 = content" framings
were both narrowed by direct inspection.*
