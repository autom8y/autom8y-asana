---
type: spec
status: draft
initiative: asr-verification-axis-landing
title: "Acceptance + Receipt Grammar — ASR Verification-Axis Landing"
sprint: SPR-V0 (acceptance seat, concurrent with the architect's design lock)
rite: 10x-dev
generator: requirements-analyst
created: 2026-08-19
authored_at_utc: "2026-08-19T14:54:36Z"
verification_deadline: "2026-08-28"   # OPERATOR-TIGHTENED at PT-00 from the myron-derived 2026-09-02
impact: high
impact_categories: [api_contract, cross_service, data_model]
evidence_grade: MODERATE   # self-ref ceiling; STRONG is unavailable to this initiative (ADVISORY §C.5, binding)
substrate_pins:
  autom8y: "3a066a5ae79cbd9d2ac5b27bfd9be6e72bf11f2b"      # DRIFTED from shape-time d9b9c92c — see §1.1
  autom8y_asana: "e3aab8d47e932d8d46588fc62e6a4906d7712c4a" # UNCHANGED since shape time
consumes:
  - services/account-status-recon/.sos/wip/frames/asr-verification-axis-landing.shape.md
  - .know/telos/asr-verification-axis-landing.md
  - autom8y-asana/.ledge/reviews/CRITIC-wsa-watermark-cure-2026-08-18.md
  - autom8y-asana/.ledge/reviews/DIAG-offers-watermark-advance-2026-08-17.md
  - .ledge/reviews/ADVISORY-telos-integrity-asr-insight-landing-2026-08-18.md
boundary: "ACCEPTANCE ONLY. This spec does not design. FORK-1/FORK-3 are the architect's to rule at SPR-V0; this spec states what a ruling must be able to PROVE, never which ruling to make."
---

# SPEC — Verification-Axis Acceptance + Receipt Grammar

> **Why this artifact exists.** The predecessor initiative was merged, deployed,
> and STRONG-attested, and never passed once. Its eunomia ADVISORY REFUSED the
> close on **receipt grammar** — a placeholder stood where a per-item receipt
> belonged. That is a structural failure, not a diligence failure: the exits were
> written so that an unfalsifiable claim could satisfy them. This spec is the
> structural cure. It fixes, per sprint leg, the exact observable, its exact
> location, and the exact predicate — so that no sprint in this wave can exit on
> a claim that could not have been false.

**Acid test for every predicate below:** *could a verifier who was not in the room
run this and get the same answer, without interpretation?* If a predicate needs a
judgement call, it is not finished.

---

## 0. Scope, and what this spec is NOT

| | |
|---|---|
| **IS** | The machine-checkable ACCEPTANCE + RECEIPT grammar for every sprint leg of the wave (V1, V2, V3, V4, I1, B2, C1, Z1). Per leg: the receipt (WHAT / WHERE / PASS predicate), the FALSE-GREEN mode it must disprove, the discriminating check, and the four-clause binding. |
| **IS NOT** | A design. It does not rule FORK-1 (hot-path manifest read), FORK-3 (SDK/ASR PR boundary), or the SDK field name. Those are the architect's at SPR-V0, running concurrently. Where this spec constrains design, it does so only by naming what a design must be able to *prove*. |
| **IS NOT** | A re-derivation of the mission, the mechanism, or the A5 refusal. Those are settled in the frame, the DIAG, and the CRITIC and are inherited, not re-litigated. |
| **IS NOT** | The QA plan. SPR-V4 builds the four-clause bundle; this spec states what that bundle must contain in order to be admissible at PT-05. |

**Binding inheritances.** CONTRACT §1.2 [A-2026-08-12] + NON-ALIASING; critic
C-1..C-9 (C-8 in particular — the four-clause test); ADVISORY §C.5 (never inherit
STRONG); the frame §9 scars (UTC epoch discipline, `origin/main` for merged state,
grade nothing self-served, probe the prior record).

---

## 1. Substrate of record

### 1.1 Pins — and a drift correction the shape could not have made

All anchors in this spec were read by this seat at `origin/main` after an explicit
`git fetch`, at **2026-08-19T14:54:36Z**. Never the working tree (frame §9 scar 2:
*a citation that resolves line-exact against your tree is not evidence the tree is
current*). The local tree at authoring time is on
`fix/wss-wildcard-scope-bypass-closure` and is **not** the substrate of record.

| Repo | Shape-time pin | **This spec's pin** | Delta |
|---|---|---|---|
| `autom8y` | `d9b9c92c` | **`3a066a5a`** | **DRIFTED.** `git diff --stat d9b9c92c origin/main -- services/account-status-recon/` = one file, `+226` lines, `.ledge/reviews/RECEIPT-al5-rehome-2026-08-17.md`. **Zero source change.** Every ASR source anchor the shape cites survives — but see §1.2, where two of them were **already wrong at shape time**. |
| `autom8y-asana` | `e3aab8d4` | **`e3aab8d4`** | UNCHANGED. All four A1 anchors re-verified by this seat (§1.3). |

**Anchor convention, used throughout.** `A8Y:` = `autom8y` @ `3a066a5a`.
`ASN:` = `autom8y-asana` @ `e3aab8d4`. An anchor without a repo prefix is
non-conformant and a verifier should refuse it.

### 1.2 Corrections this spec makes to the shape's substrate citations

Both were found by direct read, not by inference. Both are load-bearing.

| # | Shape says | **Verified at `origin/main`** | Consequence |
|---|---|---|---|
| **S-CORR-1** | ASR floor pin at `services/account-status-recon/pyproject.toml:26` | `:26` is **comment prose**. The pin is at **`:35`** (`"autom8y-core>=4.6.0,<5.0.0"`). | A sprint sent to `:26` edits a comment and reports success. See **AD-3**. |
| **S-CORR-2** | "BOTH floor pins" (root `:21` + ASR `:26`) | There is a **THIRD**: `A8Y:services/account-status-recon/pyproject.toml:79` = `"autom8y-core[testing]>=4.6.0,<5.0.0"`. | Moving two of three leaves the **test** environment resolving a different SDK floor than the runtime. See **AD-3**. |

Verified-correct as cited: root `A8Y:pyproject.toml:16` (block comment "single
source of truth for SDK minimums across all members"), `:21`
(`"autom8y-core>=3.2.0"`), `:71` (`autom8y-core = { workspace = true }`);
`A8Y:.../readiness.py` = 574 lines; `A8Y:.../rules.py:427`.

### 1.3 Anchors this seat verified by direct read

| Anchor | Verified content |
|---|---|
| `ASN:src/autom8_asana/metrics/freshness.py:735` | `def compute_verification_age(` |
| `ASN:src/autom8_asana/metrics/freshness.py:785` | `    active_names = classifier.active_sections()` — the grain defect |
| `ASN:src/autom8_asana/dataframes/builders/progressive.py:573` | `stamp_info.last_verified_at = now` |
| `ASN:src/autom8_asana/dataframes/builders/progressive.py:515-516` | `if r.verdict == ProbeVerdict.PROBE_FAILED:` / `continue` — **the RED tooth, verified to exist** |
| `ASN:src/autom8_asana/models/business/activity.py:92-94` | `def billable_sections(...)` → `ACTIVE + ACTIVATING` |
| `A8Y:.../readiness.py:522` | comment `# THE AXIS SWITCH.` |
| `A8Y:.../readiness.py:526 / :537 / :551` | the three existing dispositions: `GATE` / `REFUSE` / `else` (DORMANT) |
| `A8Y:.../orchestrator.py:1323` | `"report_posted"` — the **single** emit site |
| `A8Y:.../orchestrator.py:1326` | `abort_reason=abort_reason,` — unconditional kwarg |
| `A8Y:.../fetcher.py:285` | `CONTENT_AXIS_UNAVAILABLE_EVENT = "offers_content_axis_unavailable"` |
| `A8Y:.../fetcher.py:449` | `capability = detect_content_axis_capability()` |
| `A8Y:sdks/python/autom8y-reconciliation/.../gate.py:330 / :340 / :358` | `readiness_check_pass` (×2) / `readiness_check_fail` |
| `A8Y:sdks/python/autom8y-reconciliation/.../metrics.py:23` | `SHARED_NAMESPACE = "Autom8y/Reconciliation"` |
| `A8Y:sdks/python/autom8y-reconciliation/.../metrics.py:190-198` | `PipelineReadiness`, values `{pass:1.0, warn:0.5, fail:0.0}`, default `-1.0`, dims `Service` + `Status` |
| `A8Y:sdks/python/autom8y-log/.../processors.py:56-57` | `trace_id` = `format(..., "032x")`; `span_id` = `format(..., "016x")` |
| `A8Y:terraform/services/account-status-recon/main.tf:108` | `schedule_expression = "cron(0 */4 * * ? *)"` — **6 ticks/day, so 12 ticks = 48h exactly. The shape's pacing premise is CONFIRMED.** |
| `A8Y:terraform/services/account-status-recon/main.tf:363` | `function_name = "autom8y-account-status-recon"` |
| `A8Y:terraform/environments/production/checks.tf:78` | ECR repository `autom8y/account-status-recon` |

---

## 2. The receipt grammar

### 2.1 A receipt is a triple, or it is not a receipt

Every acceptance receipt in this wave is exactly three things. A claim missing any
one of them is **inadmissible** and the owning Potnia refuses the exit.

| Field | Meaning | Non-conformant example |
|---|---|---|
| **WHAT** | The named observable: a log event name + field, a CloudWatch metric + dimension, or an artifact path. Named literally, as it appears in the emitter. | "the logs show it passed" |
| **WHERE** | The exact surface: log group, metric namespace + dimensions, S3 URI, package index, or repo-qualified `{path}:{line}`. | "in CloudWatch" |
| **PASS predicate** | A boolean over the observable that a verifier evaluates without interpretation, including its **denominator** and its **time bounds in UTC**. | "no failures were observed" |

### 2.2 Correlation-key topology — read this before writing any same-trace predicate

The wave's telos requires several receipts "on the SAME trace." The correlation
substrate is **not uniform across the emitters**, and this is where a same-trace
predicate silently becomes unfalsifiable.

| Event | Emitter | Carries `invocation_id`? | Carries `trace_id`? |
|---|---|---|---|
| `readiness_check_pass` / `readiness_check_fail` | SDK gate, `A8Y:sdks/.../gate.py:330,:340,:358` | **NO** — kwargs are `source`, `staleness_seconds`, `threshold_seconds`, `abort_threshold_seconds` only | Yes, via the log processor, **iff inside a span** |
| `offer_freshness_axis_{clamped,refused,dormant}` | `A8Y:.../readiness.py:532,:544,:554` | **NO** | Yes, same condition |
| `readiness_gate_abort` | `A8Y:.../orchestrator.py:219-222` | **YES** (`:221`) | Yes |
| `report_posted` | `A8Y:.../orchestrator.py:1323-1329` | **YES** (`:1327`) | Yes |
| `offers_content_axis_unavailable` | `A8Y:.../fetcher.py:451-461` | **NO** | Yes, same condition |

**LAW R-1 — the join key is `trace_id`, and only `trace_id`.** The gate-side
events carry no `invocation_id`, so any join that crosses the gate↔report boundary
— which every telos conjunct does — **must** join on `trace_id`.

**LAW R-2 — `trace_id` is 32 hex characters. A 16-hex value is a `span_id`.**
`A8Y:sdks/python/autom8y-log/.../processors.py:56-57` formats `trace_id` as
`032x` and `span_id` as `016x`. The frame's cited *"all on trace
`8b6db8eea70febbc`"* is **16 hex** — a `span_id`. This is benign on the abort path
and **actively dangerous on the success path**; see **AD-2**.

**LAW R-3 — assert presence before asserting absence (the born-mute guard).**
`add_otel_trace_ids` is a no-op outside a span context
(`A8Y:sdks/python/autom8y-log/.../processors.py:53-58`, guarded on
`span_context.is_valid`). A predicate of the shape *"no event with X was found on
the trace"* is **vacuously true** when the field is absent entirely. Therefore:

> Every same-trace receipt states its **denominator first** — the count of events
> bearing the join key in the window — and a denominator of zero is a **FAIL**,
> never a pass.

This law is the generalization of the wave's born-mute scar and it applies to
every predicate in §4 that contains the word "absent."

### 2.3 Production-observable, defined for this wave

Inherited from the shape's exit-criteria doctrine and sharpened:

- **Admissible**: a fact read off the deployed system or its telemetry, in a
  declared UTC window, from a surface a third party can re-read.
- **Inadmissible**: a green unit test; a fixture; a green publish/CI job; a
  reconstructed emitter (the k1-ib1 scar: *prove against the REAL emitter*); a
  `dry_run` execution (`A8Y:.../orchestrator.py:556-560` suppresses wire egress —
  a `dry_run` receipt proves nothing about the live surface).

### 2.4 UTC + window discipline

All windows are UTC, half-open `[start, end)`, stated as ISO-8601 with an explicit
epoch. Ticks fire at `00/04/08/12/16/20` UTC (`cron(0 */4 * * ? *)`,
`A8Y:terraform/services/account-status-recon/main.tf:108`) with observed dispatch
jitter of ~60-90s (the live evidence lands at `:01`). **A tick-boundary predicate
allows a +300s dispatch tolerance and states it.** A predicate that assumes exact
`:00` will drop real ticks and under-count the denominator.

---

## 3. The four-clause test, and which clauses bind which leg

### 3.1 The test, as corrected by the critic

The operator's original two-clause form is **insufficient**: the constant `999999`
changes the quantity and goes RED on a halted warmer, and it is a stuck alarm
(CRITIC §6.2). A5 walks straight through the same hole (CRITIC §6.3). The critic's
reductio added clauses (iii) and (iv):

| Clause | Statement | What discharges it |
|---|---|---|
| **(i)** | The change alters the measured **QUANTITY** | A before/after at disposition level on the same trace shape |
| **(ii)** | The new quantity is still **RED on a genuinely-halted warmer** | A **discriminating canary**: a deliberately-broken INPUT the live surface correctly refuses, paired with the real input passing GREEN. **Two-sided or it does not count.** Injecting a defect into working production code is G-THEATER and is FORBIDDEN. |
| **(iii)** | **GREEN arm on REAL data** | An *observed* PASS on the healthy production system, on real ticks. Not a fixture, not a unit test. Had this clause existed, A5 would have been refused on sight (0/7). |
| **(iv)** | **Construct validity / discrimination** | An **OBSERVED** state in which the warm loop is healthy, the business is quiet, and the quantity is GREEN. Demonstrated, never argued. |

**Clauses (i)+(ii) alone certify a stuck alarm. This wave measures nothing against
fewer than all four.**

### 3.2 Clause-binding matrix

A clause binds a leg when that leg is where the clause's evidence is *produced*.
Legs marked `—` produce no evidence for that clause and must not claim it.

| Leg | (i) quantity | (ii) RED tooth | (iii) GREEN on real data | (iv) construct validity |
|---|---|---|---|---|
| **SPR-V1** producer | contributes | **produces the INPUT** (a reproducible halted-warmer condition) | — | contributes (grain correctness) |
| **SPR-V2** SDK | contributes (parse/refuse behavior) | **produces the refusal** on an absent field | — | — |
| **SPR-V3** ASR | **produces** (the fourth disposition) | contributes (end-to-end RED) | — | — |
| **SPR-V4** receipts | **binds** | **binds** | **binds** (the 12-tick window IS the receipt) | **binds** (the observed quiet-GREEN state) |
| **SPR-I1** interim | **N/A — and the N/A must be PROVEN** (`readiness.py` byte-identical) | N/A | N/A | N/A |
| **SPR-B2** first light | — | — | contributes (the first-light trace) | — |
| **SPR-C1** roster | — | — | — | — |
| **SPR-Z1** attest | re-derives | **re-derives with its OWN fresh construction** | re-derives | re-derives |

**The I1 row is the one most likely to be abused.** "Four-clause test not
applicable" is a *conclusion*, not a premise. SPR-I1 earns it with a byte-identical
receipt (§5), or the full test applies.

---

## 4. Per-leg acceptance blocks

Format per leg: **exit claim → receipts (WHAT/WHERE/PASS) → false-green modes +
discriminating check → REFUSE predicate.**

---

### 4.1 SPR-V1 — Producer leg (repo: `autom8y-asana`)

**Exit claim.** The deployed producer emits the verification quantity on the serve
path, at the ruled grain, and a halted-warmer RED condition is reproducible from
the producer side.

#### Receipts

| ID | WHAT | WHERE | PASS predicate |
|---|---|---|---|
| **R-V1-1** | The verification field on a **live serve-path response** from the deployed producer | The deployed asana query surface (not a fixture, not a local call) | Field present, numeric, finite, `>= 0`. Response captured **after** the deploy that carries the cure SHA, with the capture timestamp in UTC and the deployed image/commit identifier recorded alongside. |
| **R-V1-2** | Deploy latency: merge commit timestamp → first serve-path response carrying the field | asana deploy pipeline + the R-V1-1 capture | **Measured value recorded, whatever it is.** This DISCHARGES telos UV-P-1 ("~13min post-merge"). A receipt that restates "~13min" without a measurement does **not** discharge it. |
| **R-V1-3** | Grain: the in-scope section set used by the computation | `ASN:src/autom8_asana/metrics/freshness.py` (the call site replacing the `:785` hardcode) + the live response | The in-scope set derives from the request's classification via `billable_sections()` (`ASN:src/autom8_asana/models/business/activity.py:92-94`, `ACTIVE + ACTIVATING`), **not** `active_sections()`. Asserted at **POOL level only** — C-3 forbids re-tightening to section level. |
| **R-V1-4** | A reproducible genuinely-halted-warmer condition (the clause-(ii) INPUT for SPR-V4) | Named producer-side procedure + the observable it produces | The procedure is a **deliberately-broken INPUT**, stated as a runnable recipe, that the live surface correctly refuses. It is **not** an edit to working production code. |
| **R-V1-5** | The RED tooth survives a never-probed section | `ASN:.../progressive.py:515-516` + the computed verification value | A section with `last_verified_at is None` does **not** yield a fresh-looking age. See **AD-6** — this is the leg's hardest receipt and its most likely silent failure. |

#### False-green modes

| ID | Mode | Why it is invisible | **Discriminating check** |
|---|---|---|---|
| **FG-V1-1** | **Build-cache skips NEW files** (shape RISK-2). A new producer module is absent from the deployed image even after a green build. | CI is green; the merge is real; the code exists at `origin/main`. Only the *image* lacks it. | R-V1-1 is a **live serve-path** observation. A cache-skipped module cannot produce a field on a live response. Do not substitute "the build was green." |
| **FG-V1-2** | **Grain under-scope.** The field is present and plausible, computed over the 22-section `active_sections()` pool instead of the ruled billable pool. | A number appears. It is even roughly right. Nothing errors. | R-V1-3: assert the in-scope **pool identity**, not the presence of a value. A value alone is not evidence of grain. |
| **FG-V1-3** | **`written_at` backfill reads as fresh.** `compute_verification_age`'s §Decision-6 fallback substitutes `written_at` when `last_verified_at is None`. `written_at` is a **build-clock** quantity and a zero-fetch warm advances it (CRITIC §6.3: parquet watermark `03:15:22Z → 04:23:04Z` at row-count identically `4191`). A never-probed section can therefore report a *recent* verification age. | The intent documented at `ASN:.../progressive.py:524-531` is the opposite — "surfacing it as UNVERIFIED rather than false-fresh". The fallback is *designed* to climb. It only inverts when the L7-repointed defect stamps `written_at` on a zero-fetch warm. | R-V1-5, and **AD-6**: either the design refuses the backfill on the gating path (`VerificationAge.unavailable(...)` → a consumer-side REFUSAL sentinel), **or** SPR-R1's L7-repointed fix lands **before** the 12-tick window opens. This is a cross-sprint dependency the shape currently records as independent. |

#### REFUSE predicate

SPR-V1 exits REFUSED if: the field is observed only in a fixture or a local call;
or the deploy latency is asserted rather than measured; or the grain is claimed at
section level; or R-V1-5 is answered by argument rather than by an observation.

---

### 4.2 SPR-V2 — SDK leg (repo: `autom8y`, package `sdks/python/autom8y-core`)

**Exit claim.** The separately-named verification field exists on
`ResponseFreshness`, is parsed under NON-ALIASING, refuses rather than degrades
when absent, and the published version is **resolvable from the index the Lambda
build actually uses**.

#### Receipts

| ID | WHAT | WHERE | PASS predicate |
|---|---|---|---|
| **R-V2-1** | NON-ALIASING, proven | `A8Y:sdks/python/autom8y-core/src/autom8y_core/helpers/asana_freshness.py` (`FreshnessDisposition`:156, `ResponseFreshness`:170, `_parse_content_watermark`:256, `derive_response_freshness`:333) + the test file | A test asserts that an **absent** verification field does **not** fall back to `content_age_seconds`, does **not** coalesce, does **not** share a parse branch, and does **not** read as fresh. Grep receipt: zero occurrences of `or`-style coalescing on the verification path, cited by `{path}:{line}`. |
| **R-V2-2** | The AXIS-DROPPED tooth on the new axis | Test + `A8Y:.../fetcher.py:467-474` (the hazard the content axis documents) | A genuinely-absent verification column yields a **REFUSAL**, never `None`-as-PASS. See FG-V2-3 — this is the exact hole the SDK gate leaves open. |
| **R-V2-3** | **Index resolution** of the published version | The package index the Lambda build resolves from (CodeArtifact), from a **clean environment with the uv workspace excluded** | `pip download` / `uv pip install` of the exact published version succeeds **and** the installed distribution exposes the new attribute (import + `hasattr`, recorded verbatim). A green publish job is **not** this receipt. |
| **R-V2-4** | Version bump from the observed baseline | `A8Y:sdks/python/autom8y-core/pyproject.toml:7` = `version = "4.15.0"` at `3a066a5a` | Published version `> 4.15.0`, recorded literally. |

#### False-green modes

| ID | Mode | Why it is invisible | **Discriminating check** |
|---|---|---|---|
| **FG-V2-1** | **RISK-1 — workspace-editable resolution masks the published floor.** Dev and CI resolve `autom8y-core` **editable** via the uv workspace (`A8Y:pyproject.toml:71` `autom8y-core = { workspace = true }`); the deployed image resolves a **published wheel** against a floor. Everything is green locally while the image ships without the field. | This is the shape's single most-defended seam and the predecessor's exact scar: merged, deployed, attested, still dark. Nothing in the dev loop can see it. | **R-V2-3 must run with the workspace excluded.** Resolving in the monorepo checkout proves nothing — it resolves the editable source. State the isolation mechanism in the receipt (clean venv / container / `--no-sources`), and record the resolved version *and* the attribute probe. |
| **FG-V2-2** | **"The publish job went green."** Manual publishes bypass the version gate (fleet scar). A green job is not a fetchable artifact; a cold-cache CodeArtifact 401 also presents as a build problem, not a publish problem. | Job status is the most available signal and the least load-bearing one. | R-V2-3 is a **resolution**, run by the claimant's own hands, in the window. Job status is inadmissible as a substitute. |
| **FG-V2-3** | **EC-1 `None` → PASS.** The SDK gate at `A8Y:sdks/.../gate.py:328-334` reads `if staleness_seconds is None:` → `log.info("readiness_check_pass", source=..., reason="no_staleness_metadata")` → `return ReadinessStatus.PASS`. A dropped verification field that resolves to `None` therefore reads as **PASS at INFO level**. | It is a PASS, logged at INFO, on a source that produced no data at all. It looks exactly like health. | R-V2-2. The verification path must produce a **refusal sentinel** (the pattern at `A8Y:.../readiness.py:537-550`, `refusal_staleness_seconds`), never `None`. Additionally, any window-scoped PASS predicate in this wave must exclude `readiness_check_pass` events carrying `reason="no_staleness_metadata"` — **counting them as passes is the born-mute failure of the whole realization predicate.** |

#### REFUSE predicate

SPR-V2 exits REFUSED if: resolution was performed inside the workspace; or
resolution is asserted from job status; or an absent field is shown to produce
anything other than a refusal.

---

### 4.3 SPR-V3 — ASR consumption leg (repo: `autom8y`, `services/account-status-recon`)

**Exit claim.** `readiness.py` consumes the verification axis as a fourth
disposition alongside the existing switch; **all three** floor pins move; a live
tick emits the axis; the abort-rendering path is untouched.

#### Receipts

| ID | WHAT | WHERE | PASS predicate |
|---|---|---|---|
| **R-V3-1** | **All THREE floor pins moved** (S-CORR-2) | `A8Y:pyproject.toml:21`; `A8Y:services/account-status-recon/pyproject.toml:35`; `A8Y:services/account-status-recon/pyproject.toml:79` | All three floors `>=` the version published at R-V2-4, shown by a diff against `3a066a5a`. **Two of three is a FAIL**, and the ASR pin is at `:35`, not `:26`. |
| **R-V3-2** | The fourth disposition is live | `A8Y:.../readiness.py` around the axis switch (`:522` comment, `:526` GATE, `:537` REFUSE, `:551` DORMANT) | The verification disposition is a **distinct branch**, cited by `{path}:{line}` post-merge, and the three existing branches retain their current semantics. |
| **R-V3-3** | **A live tick emits the axis**, positively | Log group `/aws/lambda/autom8y-account-status-recon` | On a real `trace_id` (32 hex, LAW R-2), post-deploy, in a declared UTC window: the verification disposition event is **PRESENT** with a numeric value, **and** `offers_content_axis_unavailable` is **ABSENT** on that trace, **and** the trace's denominator is non-zero (LAW R-3). |
| **R-V3-4** | A5 refusal honored structurally | `A8Y:.../readiness.py:334-344` (whole-source dormancy, verbatim present at `3a066a5a`) | Either **byte-unchanged** (`git diff` receipt), or changed with a **full four-clause** receipt showing one dormant constituent no longer routes the whole source to the toothless build clock. |
| **R-V3-5** | Abort rendering untouched | `A8Y:.../orchestrator.py:236-262` | `git diff` shows zero change to `_build_readiness_abort_alert` and to the emissions at `:248` / `:258`. That surface belongs to SPR-I1 (constraint §7.4: the gate and the rendering never move in the same PR). |

#### False-green modes

| ID | Mode | Why it is invisible | **Discriminating check** |
|---|---|---|---|
| **FG-V3-1** | **R-6 HONEST QUIET TOLERANCE fires on the new axis.** `A8Y:.../fetcher.py:444-448` records operator ruling R-6: `detect_content_axis_capability()` (`:449`) feature-probes the installed SDK and, on absence, emits `offers_content_axis_unavailable` (`:285`, `:451-461`) and **falls back to `data_age_seconds` — the legacy build clock** — deliberately *not* a build failure (`A8Y:services/account-status-recon/pyproject.toml:28-34`). If the verification axis is plumbed through the same probe-and-fallback pattern, an unresolved published floor produces a **disclosed but PASSING** degraded gate. | This is RISK-1 with a *disclosure log attached* — which reads as diligence. The system announces its own degradation into a channel nobody is gating on, and the tick passes. It also **violates CONTRACT §1.2 NON-ALIASING**, which forbids fallback on this axis. | R-V3-3 is **two-sided by construction**: the positive verification event must be **PRESENT** *and* `offers_content_axis_unavailable` **ABSENT**, on the same 32-hex `trace_id`. Absence-of-disclosure alone is vacuous (LAW R-3). The **presence of the positive event is the discriminator.** |
| **FG-V3-2** | **Two-of-three pins.** Runtime resolves the new floor; the `[testing]` extra at `:79` does not. Tests exercise one SDK, the Lambda ships another. | The test suite is green **because** it resolved a different wheel. | R-V3-1 enumerates all three pins by `{path}:{line}` with a diff. |
| **FG-V3-3** | **Merge ≠ deployed.** ASR merge = deploy, but "deploy registered" ≠ "the image is serving" (fleet scar: `terraform apply` registers but does not roll). | The PR is merged, the pipeline is green, the function exists. | R-V3-3 is a **live tick** on a real trace, not a deployment event. PT-04 then pins the boundary to the **first ECR image containing the cure SHA** (§4.8, leg (a)). |

#### REFUSE predicate

SPR-V3 exits REFUSED if: fewer than three pins moved; or R-V3-3 rests on absence
alone; or the abort-rendering surface was touched in the same PR.

---

### 4.4 SPR-V4 — The four-clause receipt bundle (builder-side)

**Exit claim.** All four clauses discharged against the **deployed** cure. This is
builder-side evidence and is explicitly **not** the attestation — SPR-Z1 inherits
none of it.

#### Receipts

| ID | Clause | WHAT / WHERE | PASS predicate |
|---|---|---|---|
| **R-V4-i** | (i) quantity changed | Disposition-level before/after on the same trace shape; log group `/aws/lambda/autom8y-account-status-recon` | Pre-boundary trace shows the offers staleness sourced from the content axis; post-boundary trace shows it sourced from the verification axis. Both traces named by 32-hex `trace_id` + UTC timestamp. |
| **R-V4-ii** | (ii) RED tooth | The discriminating canary built on the R-V1-4 recipe | **Two-sided, both arms recorded**: the deliberately-broken INPUT is REFUSED (RED), and the real input on the same surface PASSes (GREEN). One arm is not a proof. **Production-defect injection is G-THEATER and is FORBIDDEN** — a canary that required editing working production code is inadmissible and the sprint refuses rather than files it. |
| **R-V4-iii** | (iii) GREEN on real data | The elapsed 12-tick window | Denominator = **12** ticks (48h at `cron(0 */4 * * ? *)`), boundary-anchored per PT-04, +300s dispatch tolerance. **Every** offers-axis evaluation PASSes on the verification axis. Any exception carries a **disclosed genuine warmer/probe-failure receipt on the same 32-hex `trace_id`**. `readiness_check_pass` events with `reason="no_staleness_metadata"` **do not count as passes** (FG-V2-3). |
| **R-V4-iv** | (iv) construct validity | An **observed** system state, named by `trace_id` + UTC timestamp | Exhibit a tick where: the warm loop is healthy **and** the business is quiet (no billable-pool edit in the preceding hour, established from the manifest at **pool level**, C-3) **and** the quantity is GREEN. This is the state the old axis could never produce. |

#### False-green modes

| ID | Mode | **Discriminating check** |
|---|---|---|
| **FG-V4-1** | **G-THEATER.** A defect injected into working production code produces a RED, which is then filed as clause (ii). | The canary is a broken **INPUT**, and the receipt states the input's construction. If the recipe contains an edit to a production code path, refuse. |
| **FG-V4-2** | **Clause (iv) argued, not observed.** "There exists a state where…" is a construct-validity *argument*; the clause demands an *observation*. This is the exact substitution the critic's reductio was written to block. | R-V4-iv names a `trace_id` and a UTC timestamp, or it is not discharged. PT-05 asks this question literally. |
| **FG-V4-3** | **Window rationalized.** A failure inside the 12 ticks is explained as a quiet weekend. | Doctrine, restated as a predicate: post-cure a failure inside the window **FALSIFIES the cure**. There is no business-quiet excuse by construction. Only a *disclosed genuine warmer/probe-failure receipt on the same trace* excuses a tick, and it must name the failure. |
| **FG-V4-4** | **Denominator drift.** The window is counted from a log-window guess, or the old `0-of-47` record is silently continued into the new one. | PT-04 pins the boundary to the first ECR image containing the cure SHA; the pre-boundary record is **explicitly closed out** and the new denominator starts at zero with its own boundary stated. |

---

### 4.5 SPR-I1 — Interim posture, and the born-mute wall

**Exit claim (scope set by the PT-00 operator ruling — I-1 loud-degraded 2-of-3).**
The 6x/day abort noise is replaced by an honestly-disclosed degraded report,
**and every gate-observing surface is proven still live.**

> **This is the born-mute wall.** The success-deadman must stay honest. The
> failure mode this leg exists to prevent is not a bad report — it is a report
> that looks better *because the alarm went quiet*. The three conjuncts below are
> **not three receipts; they are one receipt on one trace.** Split across traces,
> they prove nothing: a degraded report on trace A and a `readiness_check_fail` on
> trace B are consistent with the gate having been silenced on trace A.

#### R-I1-1 — the three-conjunct same-trace receipt (**all on ONE 32-hex `trace_id`**)

| Conjunct | WHAT | WHERE | PASS predicate |
|---|---|---|---|
| **(a) the loud degraded report posted** | `report_posted` | log group `/aws/lambda/autom8y-account-status-recon`; emitter `A8Y:.../orchestrator.py:1323-1329` | Event present on trace `T`, with `content_hash` present and non-empty, and the degraded-disclosure content observable in the `#account-health` post itself. |
| **(b) the gate still failing, loudly** | `readiness_check_fail` with `source="offers"` | same log group; emitter `A8Y:sdks/.../gate.py:357-362` | Event present on the **same trace `T`**, with a numeric `staleness_seconds`. **Presence is the predicate** — the disclosure must not have replaced the failure signal. |
| **(c) `PipelineReadiness` NOT flipped** | CloudWatch metric `PipelineReadiness` | namespace `Autom8y/Reconciliation` (`A8Y:sdks/.../metrics.py:23`), dims `Service=account-status-recon` + `Status`; emitted `A8Y:sdks/.../metrics.py:190-198` | Value at the tick corresponding to trace `T` is **`0.0` with `Status="fail"`**. The value map is `{pass:1.0, warn:0.5, fail:0.0}` with `-1.0` for unknown. **`1.0` or `0.5` is a FAIL of this receipt** — it means the interim rendering reached the readiness verdict, which it must never do. |

**Denominator statement (LAW R-3).** The receipt states the count of ticks in the
window and shows the conjunction holding on **every** one, not on a selected tick.
A single hand-picked trace is a selection on the dependent variable — the exact
defect C-4 corrected in the DIAG.

#### R-I1-2 — gate byte-identical

| WHAT | WHERE | PASS predicate |
|---|---|---|
| `git diff` over the gate module | `A8Y:services/account-status-recon/src/account_status_recon/readiness.py` | **Zero bytes changed** across the SPR-I1 PR, shown by an explicit diff receipt against the pre-PR `origin/main` SHA. This is what earns the "four-clause test not applicable" conclusion (§3.2). Without it, the full four-clause test applies. |

#### R-I1-3 — telemetry intact

| WHAT | WHERE | PASS predicate |
|---|---|---|
| `readiness_check_fail`, the GAP-1 never-missing dead-man (`A8Y:.../orchestrator.py:262`, emitter `:1079-1099`), the L6 alarm lane | log group + alarm state | Each still fires at its pre-change rate over a window of equal length before and after. **Nothing observing the gate goes dark.** A rate that drops is a FAIL even if the report looks better. |

#### False-green modes

| ID | Mode | **Discriminating check** |
|---|---|---|
| **FG-I1-1** | **The success-deadman goes quiet.** The rendering change reaches the readiness verdict; `PipelineReadiness` flips to `warn`/`pass`; the alarm lane stops seeing failure. The channel looks healthier and the gate is blind. | R-I1-1(c) — the metric value at the same tick is `0.0`/`Status="fail"`. This is the born-mute wall's teeth. |
| **FG-I1-2** | **Cross-trace assembly.** (a), (b), (c) each observed, on different traces, and reported as a conjunction. | Single 32-hex `trace_id`, stated literally in the receipt, for all three conjuncts. |
| **FG-I1-3** | **Quiet normalization** (shape RISK-4). The degraded banner becomes wallpaper; nobody chases the cure. | The receipt names the specific anti-normalization property preserved (CARD-SCAR-016 trained-ignore class) and states it as an observable in the rendered post, not as an intention. |
| **FG-I1-4** | **Wrong surface.** A sprint sent to `report.py` finds nothing to edit and reports "no change needed." | `A8Y:.../report.py` (510 lines) contains **zero** occurrences of `abort_reason`; the abort is built and posted from `A8Y:.../orchestrator.py` (`_build_readiness_abort_alert`, emissions at `:248`/`:258`). The receipt cites the edited `{path}:{line}`. |

**If the ruling had been I-4 (any gate-side interim):** the full four-clause test
applies, **and** the sprint must first answer `A8Y:.../readiness.py:334-344`
whole-source dormancy **and** the 0-of-7 PASS measurement. Absent those two, it
REFUSES rather than proceeds.

---

### 4.6 SPR-B2 — First light + clarity close

**Exit claim.** The first real clarity report renders in `#account-health`, and
telos conjunct 3 is discharged.

#### Receipts

| ID | WHAT | WHERE | PASS predicate |
|---|---|---|---|
| **R-B2-1** | **First light**, on one trace | log group `/aws/lambda/autom8y-account-status-recon` | On a single 32-hex `trace_id`: `report_posted` with **`abort_reason == "report_success"`** (see **AD-1** — "no `abort_reason`" is unsatisfiable), **and** `content_hash` present and non-empty, **and** metric `SourceCoverage3of3 > 0` (namespace `Autom8y/Reconciliation`, `A8Y:sdks/.../metrics.py:48`) at that tick. |
| **R-B2-2** | Offers PASSed **on the verification axis**, not by dormancy | same trace | `readiness_check_pass` with `source="offers"` present, **and** `offer_freshness_axis_dormant` (`A8Y:.../readiness.py:554`) **ABSENT**, **and** the verification disposition event **PRESENT** on that trace. |
| **R-B2-3** | The clarity lever applied at its **current** location | `A8Y:services/account-status-recon/src/account_status_recon/rules.py:427` (`_ADVISORY_VERDICTS`; comment at `:414`) | Diff touches `:427`, not `:421`. The BRIEF's cited `:421` has moved; **anyone editing `:421` is editing the wrong line.** |
| **R-B2-4** | The clarity wave is CLOSED | session ledger for `session-20260810-151912-d7e932ce` | Session wrapped, read from the ledger. **Never infer wrap from rite state.** |

#### False-green modes

| ID | Mode | **Discriminating check** |
|---|---|---|
| **FG-B2-1** | **The report posts for the wrong reason.** Offers goes DORMANT (`A8Y:.../readiness.py:551-554`), `offer_staleness = data_age` — the toothless build clock — the gate passes, the report posts. Identical user-visible outcome, zero cure. **This is A5-literal arriving through the back door.** | R-B2-2: `offer_freshness_axis_dormant` **ABSENT** *and* the verification event **PRESENT**, same trace. Absence alone is vacuous (LAW R-3). |
| **FG-B2-2** | **`abort_reason` deleted to satisfy the literal telos wording.** Someone reads conjunct 3 as written and removes the field. | **AD-1.** The field is an unconditional kwarg (`A8Y:.../orchestrator.py:1326`) with a documented enum (`:1249-1250`) and an AP-9 binding call-site convention (`:533-535`). Deleting it destroys the 1:1 `slack_post_attempt` ↔ `report_posted` breadcrumb. The corrected predicate is `abort_reason == "report_success"`. |

---

### 4.7 SPR-C1 — Insight materialization (f-1 → C5 roster)

**Exit claim.** The 24-candidate roster is materialized and observable, including
Premier.

#### Receipts

| ID | WHAT | WHERE | PASS predicate |
|---|---|---|---|
| **R-C1-1** | The proceed-check, **both legs, in order** | Recorded in the sprint receipt | Leg 1 = F1a substrate; leg 2 = insight-503. Both results recorded **whatever the outcome**, in order. **Entry is the proceed-check, never a tick count** — inferring readiness from a passed tick is the predecessor's error, corrected by HANDOFF §9.5. |
| **R-C1-2** | The roster, materialized | The operator-observable surface (`#account-health` / the emission target) | Count **= 24** *and* **Premier present by name**. The count alone is not the predicate — a 24-count without Premier is a different roster. |
| **R-C1-3** | DEFER-S7 untouched | Sprint record | No sprint, alias, or sub-task of this initiative dispatched the insight-503 disjoint attestation. |

#### False-green modes

| ID | Mode | **Discriminating check** |
|---|---|---|
| **FG-C1-1** | **Logged, not surfaced.** The roster is computed and appears in telemetry but never reaches the operator's eye. | R-C1-2 is observed on the **operator-visible surface**, not in a log line. |
| **FG-C1-2** | **Count coincidence.** 24 rows match by arithmetic while the named candidate is missing. | Premier **by name**. The name is the discriminator; the count is not. |
| **FG-C1-3** | **Entry inferred from a passing tick.** Once the V-lane lands, ticks pass, and the emission is opened on that basis. | R-C1-1: the two ordered legs are the entry, and they are recorded. |

---

### 4.8 SPR-Z1 — Rite-disjoint realization attestation (RESERVED, single-use)

**ENTRY = the telos `verified_realized` evidence list, verbatim, in full. All five,
or the sprint does not open.** Reproduced here from
`A8Y:.know/telos/asr-verification-axis-landing.md:34-39` without alteration:

1. *"deploy boundary pinned by the attester's own hands (first ECR image
   containing the cure SHA — the critic's C-4 method, never a log-window guess)"*
2. *"within the first 12 ticks (48h) post-boundary: EVERY offers axis evaluation
   PASSes on verification_age (any exception carries a disclosed genuine
   warmer/probe-failure receipt on the same trace)"*
3. *"at least one report_posted with NO abort_reason + content_hash logged +
   SourceCoverage3of3 > 0 on the SAME trace_id"* — **operationalized per AD-1 as
   `abort_reason == "report_success"`; the literal wording is unsatisfiable
   against the emitter and must not be read literally.**
4. *"four-clause receipts: RED-tooth on a genuinely-halted warmer (clause ii,
   discriminating-canary discipline — broken INPUT, never defect injection) AND
   GREEN-arm on real production ticks (clause iii)"*
5. *"C5 re-emission receipt: 24-candidate roster materialized (incl. Premier)"*

#### The three non-substitutable legs, each with its own receipt

No leg substitutes for another. A green test is not a live CLI; a live surface is
not a teeth-proof; a teeth-proof is not a clean re-run. **The attester inherits
NONE of the builder's or QA's proofs — it re-derives each leg with its own hands.**

| Leg | Altitude | WHAT / WHERE | PASS predicate |
|---|---|---|---|
| **(a)** | **receipts-exist** | The keystone re-run **UNCACHED**, by the attester | The attester itself pins the deploy boundary: enumerate ECR images for repository `autom8y/account-status-recon` (`A8Y:terraform/environments/production/checks.tf:78`), identify the **first image whose contents carry the cure SHA**, record its digest + push timestamp in UTC. **A log-window guess is not a boundary** (C-4). Then re-run the window count from that boundary, uncached, and state the denominator. |
| **(b)** | **discrimination** | The teeth re-proved with the attester's **OWN fresh construction** | The attester builds its **own** deliberately-broken INPUT — **not** the SPR-V4 fixture — and shows both arms: broken input REFUSED, real input PASSing. Reusing SPR-V4's canary collapses leg (b) into leg (a) and the attestation loses a leg. |
| **(c)** | **user-surface** | The live `#account-health` surface, observed **DIRECTLY** | The attester reads the actual channel and records what a human sees: the ranked de-noised same-day 3-of-3 report + the standing C5 roster. Telemetry is **not** this leg. The mission is what the cofounder sees. |

#### Additional Z1 exit predicates

| ID | Predicate |
|---|---|
| **R-Z1-1** | A **two-valued** verdict: `ATTESTED` or `NOT-ATTESTED`. *"Attested with reservations"* is not a value. |
| **R-Z1-2** | **Every** shipped-class claim carries a repo-qualified `{path}:{line}` receipt **BEFORE** assertion. The predecessor earned its REFUSE-ADVISORY for a placeholder where a receipt belonged. |
| **R-Z1-3** | Self-grade capped at **MODERATE**. Ambiguity rounds toward the weaker grade. STRONG is unavailable to this initiative (ADVISORY §C.5). |
| **R-Z1-4** | Disjointness disclosed, including residual cognitive adjacency via the shared session root. **Disjoint methods are not disjoint attesters.** |

#### False-green modes

| ID | Mode | **Discriminating check** |
|---|---|---|
| **FG-Z1-1** | **Inheritance.** The attester reads the builder's receipts, finds them coherent, and attests. Coherence of an inherited record is not evidence about the world. | Each of (a)(b)(c) states the command the **attester** ran and its verbatim output. A leg citing another sprint's artifact as its evidence is not discharged. |
| **FG-Z1-2** | **Leg collapse.** (b) is discharged by re-reading SPR-V4's canary; (c) by reading telemetry instead of the channel. | Leg (b) requires an **own fresh construction**; leg (c) requires the **channel**, observed directly. |
| **FG-Z1-3** | **Spent early.** SPR-Z1 fires on a design review, a build receipt, or a partial close. It is single-use; the initiative then has no true exit. | PT-05 is a hard gate whose `on_fail` is literally *"DO NOT SPEND SPR-Z1."* Entry is the five-item list above, in full. |
| **FG-Z1-4** | **Dispatcher-critic degeneracy.** The attestation is produced from a context that is not rite-disjoint. | `verification-auditor` is **absent** from `services/account-status-recon`; dispatch from the monorepo root or from `autom8y-asana`. **Never substitute a same-rite agent with a similar name** — change the cwd. |

---

## 5. Acceptance requirements — MoSCoW

Prioritized by the challenge test: *what happens if we ship without this?* An item
is **MUST** only when the honest answer is "an exit becomes unfalsifiable."

| ID | Requirement | Priority | Rationale / workaround |
|---|---|---|---|
| AR-01 | Same-trace joins use the 32-hex `trace_id`; `span_id` is never the join key | **MUST** | Without it, the success path yields a FALSE-RED (AD-2). No workaround. |
| AR-02 | Every same-trace receipt states its denominator before any absence claim | **MUST** | Absence over an absent field is vacuous. This is the born-mute class. |
| AR-03 | Conjunct 3 evaluated as `abort_reason == "report_success"` | **MUST** | The literal wording is unsatisfiable (AD-1); ships as either a permanent false-FAIL or a destructive "fix." |
| AR-04 | SPR-V1 exits on a live serve-path observation from the deployed producer | **MUST** | Build-cache skip is otherwise invisible (FG-V1-1). |
| AR-05 | SPR-V2 index resolution runs with the uv workspace excluded | **MUST** | RISK-1 is otherwise undetectable before the deploy. |
| AR-06 | All **three** `autom8y-core` floor pins move together | **MUST** | Test/runtime SDK divergence (AD-3). |
| AR-07 | SPR-V3 exits two-sided: verification event PRESENT **and** `offers_content_axis_unavailable` ABSENT | **MUST** | R-6 quiet tolerance otherwise passes a degraded gate (AD-4). |
| AR-08 | Clause (ii) is a two-sided discriminating canary on a broken **INPUT** | **MUST** | Defect injection is G-THEATER; one-sided proves nothing. |
| AR-09 | Clause (iii) is the real 12-tick window, `no_staleness_metadata` passes excluded | **MUST** | EC-1 otherwise counts data-absence as health (AD-5). |
| AR-10 | Clause (iv) names an **observed** trace + UTC timestamp | **MUST** | An argued clause (iv) is the reductio the critic blocked. |
| AR-11 | SPR-I1's three conjuncts hold on **one** trace, every tick in the window | **MUST** | The born-mute wall. Cross-trace assembly proves nothing. |
| AR-12 | SPR-Z1's three legs are each re-derived by the attester | **MUST** | Inheritance is the predecessor's exact failure. |
| AR-13 | Every receipt carries a repo-qualified `{path}:{line}` anchor | **MUST** | The literal REFUSE predicate of the close gate. |
| AR-14 | The `written_at` backfill is refused on the gating path, **or** SPR-R1's L7 fix lands before the window opens | **MUST** | Otherwise clause (ii)'s tooth is defeasible inside the window (AD-6). |
| AR-15 | PT-04 pins the boundary to the first ECR image containing the cure SHA | **MUST** | Telos conjunct 1; an unpinned boundary makes every PASS/FAIL uninterpretable. |
| AR-16 | SPR-V1 records the **measured** deploy latency (UV-P-1) | SHOULD | Workaround: carry UV-P-1 forward undischarged on the HANDOFF DEFER tag. Costs a premise, not an exit. |
| AR-17 | Grain assertions stay **pool-level** (C-3) | SHOULD | A section-level claim over-tightens the evidence; the exit still stands at pool level. |
| AR-18 | SPR-B2 asserts `offer_freshness_axis_dormant` ABSENT | SHOULD | Strong discriminator for FG-B2-1, but AR-07's positive event already carries most of the weight. |
| AR-19 | SPR-C1 records both proceed-check legs in order, and Premier by name | SHOULD | Conjunct 5 is the least coupled to the cure; a partial roster receipt is recoverable. |
| AR-20 | Receipts are re-runnable as saved CloudWatch Insights queries | COULD | Reduces Z1's re-derivation cost. Manual re-derivation is acceptable. |
| AR-21 | `span_id` recorded alongside `trace_id` for span-topology debugging | COULD | Diagnostic convenience only. |
| AR-22 | A CloudWatch-metric-derived value substituting for a log-derived same-trace join | **WON'T** | Breaks same-trace discipline; FORK-1 OPT-6 must clear this objection before it can even be selected. |
| AR-23 | Any receipt produced under `dry_run` | **WON'T** | `A8Y:.../orchestrator.py:556-560` suppresses wire egress; a `dry_run` receipt is about a suppressed path. |

**Distribution: 15 MUST / 4 SHOULD / 2 COULD / 2 WON'T (15 of 23 = 65% MUST).**
Below the 70% inflation threshold. Each MUST was challenged individually; the four
demoted to SHOULD each have a stated workaround that costs a premise rather than an
exit.

---

## 6. Consolidated receipts table — the template the wave's close populates

> **This template is the artifact the close is graded on.** The predecessor was
> REFUSE-ADVISORY'd for leaving a placeholder in exactly this position while
> asserting `shipped: PARTIAL`. **Per-item repo-qualified `{path}:{line}` anchors
> are mandatory.** A row whose anchor column reads `TBD`, `see PR`, `pending`, or
> is empty is a **close-gate REFUSE**, not a formatting nit.

| # | Receipt ID | Leg | Claim (one line) | WHAT (event / metric / artifact) | WHERE (log group / namespace / path) | PASS predicate (as evaluated) | Evidence anchor — **repo-qualified `{path}:{line}` REQUIRED** | UTC window | Verdict | Grade |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | R-V1-1 | V1 | | | | | | | PASS/FAIL | MODERATE |
| 2 | R-V1-2 | V1 | | | | | | | | |
| 3 | R-V1-3 | V1 | | | | | | | | |
| 4 | R-V1-4 | V1 | | | | | | | | |
| 5 | R-V1-5 | V1 | | | | | | | | |
| 6 | R-V2-1 | V2 | | | | | | | | |
| 7 | R-V2-2 | V2 | | | | | | | | |
| 8 | R-V2-3 | V2 | | | | | | | | |
| 9 | R-V2-4 | V2 | | | | | | | | |
| 10 | R-V3-1 | V3 | | | | | | | | |
| 11 | R-V3-2 | V3 | | | | | | | | |
| 12 | R-V3-3 | V3 | | | | | | | | |
| 13 | R-V3-4 | V3 | | | | | | | | |
| 14 | R-V3-5 | V3 | | | | | | | | |
| 15 | R-V4-i | V4 | | | | | | | | |
| 16 | R-V4-ii | V4 | | | | | | | | |
| 17 | R-V4-iii | V4 | | | | | | | | |
| 18 | R-V4-iv | V4 | | | | | | | | |
| 19 | R-I1-1 | I1 | | | | | | | | |
| 20 | R-I1-2 | I1 | | | | | | | | |
| 21 | R-I1-3 | I1 | | | | | | | | |
| 22 | R-B2-1 | B2 | | | | | | | | |
| 23 | R-B2-2 | B2 | | | | | | | | |
| 24 | R-B2-3 | B2 | | | | | | | | |
| 25 | R-B2-4 | B2 | | | | | | | | |
| 26 | R-C1-1 | C1 | | | | | | | | |
| 27 | R-C1-2 | C1 | | | | | | | | |
| 28 | R-C1-3 | C1 | | | | | | | | |
| 29 | R-Z1-a | Z1 | | | | | | | | |
| 30 | R-Z1-b | Z1 | | | | | | | | |
| 31 | R-Z1-c | Z1 | | | | | | | | |
| 32 | R-Z1-1..4 | Z1 | | | | | | | | |

**Close-gate checklist over this table (all must hold):**

- [ ] Every row's anchor column contains a repo-qualified `{path}:{line}` or a
      verbatim command + output. No `TBD`. No bare PR reference.
- [ ] Every same-trace row states a 32-hex `trace_id` and a non-zero denominator.
- [ ] No row is graded STRONG.
- [ ] Surviving UV-P items ride the HANDOFF DEFER tag (RULE-2).
- [ ] Defer-watch entries are wired, **or** the refusal to wire them is recorded
      explicitly (PT-06).

---

## 7. Acceptance defects found in the inherited predicate

These are findings **against the wave's own exit criteria**, produced by reading
the emitters rather than the plan. Each is an escalation to the architect (SPR-V0)
and to Potnia.

| ID | Severity | Finding | Anchor | Required correction |
|---|---|---|---|---|
| **AD-1** | **BLOCKING** | **Telos conjunct 3 is unsatisfiable as written.** *"at least one `report_posted` with NO `abort_reason`"* can never be observed: `report_posted` has exactly one emit site and `abort_reason` is an unconditional kwarg with a documented four-value enum; the success path passes `"report_success"` to preserve the AP-9 call-site convention. | `A8Y:.../orchestrator.py:1323` (sole emit), `:1326` (kwarg), `:1226` (default `"unknown"`), `:1249-1250` (enum), `:533-535` + `:539` + `:549` (success path) | Read conjunct 3 as `abort_reason == "report_success"`. **Do not delete the field** — that destroys the 1:1 `slack_post_attempt` ↔ `report_posted` breadcrumb and the enum convention. |
| **AD-2** | **BLOCKING** | **`trace_id` vs `span_id`.** The frame cites *"trace `8b6db8eea70febbc`"* — 16 hex, i.e. a `span_id`. On the **abort** path, gate events and `report_posted` share `readiness_span`, so span matching works by coincidence. On the **success** path `report_posted` is emitted under `report_span` — a **different span, same trace**. A span-keyed predicate therefore **FALSE-REDs the exact success path the cure produces.** | `A8Y:sdks/python/autom8y-log/.../processors.py:56-57`; `A8Y:.../orchestrator.py:198` (`reconciliation.readiness_gate` span), `:251-261` (abort post under `readiness_span`), `:499` (`reconciliation.report` span — **a different span**), `:542-552` + `:548` (success post under `report_span`) | Join on 32-hex `trace_id` only (LAW R-1/R-2). Record `span_id` as diagnostic, never as the key. |
| **AD-3** | **HIGH** | **Floor pins: wrong line + a missing third pin.** The shape names ASR `pyproject.toml:26`; `:26` is comment prose and the pin is at `:35`. A third pin exists at `:79` (`autom8y-core[testing]`) and is unnamed anywhere in the shape. | `A8Y:services/account-status-recon/pyproject.toml:35`, `:79`; `A8Y:pyproject.toml:21` | Move all three. State all three in R-V3-1. |
| **AD-4** | **HIGH** | **R-6 HONEST QUIET TOLERANCE is a live fallback that NON-ALIASING forbids on this axis.** `fetch_offers` feature-probes the installed SDK and, on absence, falls back to `data_age_seconds` with a disclosure log — deliberately not a build failure. Plumbing the verification axis through the same pattern converts RISK-1 from a hard failure into a **disclosed passing degradation**. | `A8Y:.../fetcher.py:444-448` (the R-6 comment), `:449` (probe), `:285` + `:451-461` (the disclosure), `A8Y:services/account-status-recon/pyproject.toml:28-34` (the ruling text) | SPR-V0 must rule explicitly whether R-6 tolerance extends to the verification axis. CONTRACT §1.2 says it must not. R-V3-3 is written two-sided so the answer is observable either way. |
| **AD-5** | **HIGH** | **EC-1 `None` → PASS is the born-mute hole at the gate itself.** A `None` staleness logs `readiness_check_pass` with `reason="no_staleness_metadata"` at INFO and returns PASS. Data-absence is indistinguishable from health in any naive pass-count. | `A8Y:sdks/python/autom8y-reconciliation/.../gate.py:328-334` | Every pass-count predicate in this wave **excludes** `readiness_check_pass` events carrying `reason="no_staleness_metadata"`. SPR-V2's absent-field behavior must be a refusal sentinel, never `None`. |
| **AD-6** | **HIGH** | **The §Decision-6 `written_at` backfill couples the V-lane to SPR-R1, which the shape records as independent.** `compute_verification_age` falls back to `written_at` when `last_verified_at is None`. That is *designed* to surface UNVERIFIED (the age climbs). It **inverts to false-fresh** if a zero-fetch warm re-stamps `written_at` — which is precisely SPR-R1's L7-repointed defect, independently proven by the critic (watermark `03:15:22Z → 04:23:04Z` at row-count identically `4191`). | `ASN:src/autom8_asana/metrics/freshness.py:747-750` (the backfill), `ASN:.../progressive.py:524-531` (the intent), CRITIC §6.3 (the zero-fetch proof) | Either the design refuses the backfill on the **gating** path (`VerificationAge.unavailable(...)` → consumer REFUSAL sentinel), **or** SPR-R1's L7 fix lands **before** the 12-tick window opens. **A dependency edge SPR-R1 → PT-04 that the shape does not currently carry.** |
| **AD-7** | **MED** | **The helper's documented caller contract degrades to the mutation axis.** `compute_verification_age`'s docstring states that on an empty join *"The reader's caller degrades to the mutation-axis signal in that case."* The mutation axis **is** the business-activity quantity this wave ruled construct-invalid. | `ASN:src/autom8_asana/metrics/freshness.py:751-755` | SPR-V0 must rule this out for the gating path: unavailable → **refuse**, never degrade. This is coalescing, which NON-ALIASING forbids. |

### 7.1 One premise VERIFIED (recorded because it is load-bearing and was assumed)

The telos's determinism claim — *"`last_verified_at` advances ONLY on live
non-`PROBE_FAILED` probes"* — is the entire basis for "waiting is no longer a
variable." This seat verified it rather than inheriting it:

```
ASN:src/autom8_asana/dataframes/builders/progressive.py:515-516
    for r in probe_results:
        if r.verdict == ProbeVerdict.PROBE_FAILED:
            continue
```

**CONFIRMED at `origin/main` `e3aab8d4`.** The RED tooth exists structurally. So
does the shape's pacing premise: `cron(0 */4 * * ? *)`
(`A8Y:terraform/services/account-status-recon/main.tf:108`) = 6 ticks/day, so
12 ticks = 48h exactly.

---

## 8. Open questions, UV-P register, and boundaries

### 8.1 Open questions for the architect at SPR-V0 (acceptance-side only)

| # | Question | Why acceptance cares |
|---|---|---|
| OQ-1 | Does R-6 HONEST QUIET TOLERANCE extend to the verification axis? | AD-4. Determines whether R-V3-3's `offers_content_axis_unavailable`-absent conjunct is sufficient or whether a second disclosure event must be added to the grammar. |
| OQ-2 | On an empty verification join, does the consumer **refuse** or **degrade**? | AD-6/AD-7. A degrade path makes clause (ii) defeasible and the RED tooth conditional. |
| OQ-3 | What is the named verification disposition **event name**? | Every "PRESENT" predicate in §4.3, §4.6 and §4.8 needs a literal event name. Until it is fixed, those predicates carry a placeholder and are not machine-checkable. **This is the one open dependency between the design lock and this spec.** |
| OQ-4 | Does SPR-R1's L7 fix need to precede PT-04? | AD-6. If yes, the shape's "SPR-R1 is independent" edge is wrong and PT-04 acquires a precondition. |

### 8.2 UV-P register (this spec's own open premises)

```
[UV-P: the ASR Lambda image resolves autom8y-core from CodeArtifact rather than
from the uv workspace | METHOD: inspect the Lambda build path | REASON: inherited
from shape UV-P-7, NOT observed end-to-end by this seat. It is RISK-1's premise and
therefore AR-05's premise. Discharge at SPR-V0/FORK-3.]

[UV-P: the verification disposition event name and field name | METHOD: read the
SPR-V0 design artifact when it lands | REASON: fixed by the concurrent design lock,
not by this seat. Every "PRESENT" predicate above carries it as a placeholder until
then — OQ-3.]

[UV-P: the observed ~60-90s tick dispatch jitter generalizes to a +300s tolerance
| METHOD: measure dispatch offset across the 12-tick window at SPR-V4 | REASON:
derived from the frame's live evidence at :01 plus the cron at :00; the bound is
chosen conservatively, not measured across a population.]

[UV-P: the GAP-1 dead-man and the L6 alarm lane fire at a measurable pre-change
rate suitable for the R-I1-3 before/after comparison | METHOD: measure the
pre-change rate before the SPR-I1 merge | REASON: R-I1-3 assumes a non-zero
baseline exists to compare against; EXT-DEP-2 (#1643, the L6 re-home) was DIRTY at
shape time and may not have landed.]
```

### 8.3 Explicitly out of scope for this spec

Design rulings (FORK-1, FORK-3, the field name); the TDD; test implementation;
S7 dispatch (operator-only, never dispatched); operator card execution; the EBI /
Calendly front; monolith-leg retirement; enrollment split-brain; any re-negotiation
of the frozen WATERMARK CONTRACT.

---

## 9. Evidence grade + attestation

**Grade: `[STRUCTURAL | MODERATE]`.** Single-seat, self-authored, no external
corroboration at authoring time. **STRONG is unavailable to this initiative at all**
(ADVISORY §C.5, binding): disjoint methods are not disjoint attesters; same-rite
convergence caps at MODERATE; ambiguity rounds toward the weaker grade.

The **substrate probes** in §1.2, §1.3, §7 and §7.1 are mechanical and reproducible
— each names a repo, an `origin/main` SHA, and a `{path}:{line}` — and a verifier
can re-run every one. The **acceptance judgement** built on them is a single
vantage and is exactly what SPR-VC and PT-01 exist to test.

### Attestation table

| Artifact | Absolute path | State |
|---|---|---|
| This spec | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/SPEC-verification-axis-acceptance-2026-08-19.md` | AUTHORED (draft), verified by Read |
| Shape (consumed) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y/services/account-status-recon/.sos/wip/frames/asr-verification-axis-landing.shape.md` | READ in full (1383 lines) |
| Frame (consumed) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y/services/account-status-recon/.sos/wip/frames/asr-verification-axis-landing.md` | READ in full (473 lines) |
| Telos (consumed) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y/.know/telos/asr-verification-axis-landing.md` | READ in full; deadline **2026-08-28** (operator-tightened at PT-00) |
| Critic (consumed) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/CRITIC-wsa-watermark-cure-2026-08-18.md` | READ §6.2, §6.3, §7 (C-1..C-9), §8 |
| Substrate — `autom8y` | `origin/main` = `3a066a5ae79cbd9d2ac5b27bfd9be6e72bf11f2b` | Fetched + read at 2026-08-19T14:54:36Z. Working tree (`fix/wss-wildcard-scope-bypass-closure`) NOT used. |
| Substrate — `autom8y-asana` | `origin/main` = `e3aab8d47e932d8d46588fc62e6a4906d7712c4a` | Fetched + read at 2026-08-19T14:54:36Z |

**Scars honored in the authoring of this spec:** `origin/main` for every
merged-state claim (and the ASR anchors were re-verified at a pin the shape had not
seen); UTC epoch discipline on every probe and window; MODERATE self-grade ceiling;
no STRONG anywhere; the canonical prior record (`.ledge/`) searched before any
finding was called new.
