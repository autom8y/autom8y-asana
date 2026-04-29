---
type: review
status: proposed
artifact_type: chaos-critique
rite: sre
initiative: admin-cli-oauth-migration-wave-1
sprint: wave-1-terraform-stubs
date: 2026-04-22
author: chaos-engineer
subject: platform-engineer
subject_artifact: autom8y/terraform/services/auth/observability/cloudwatch-alarms.tf
subject_line_count: 406
subject_sha: (uncommitted working-tree 2026-04-22T10:15Z)
evidence_grade: STRONG
evidence_grade_rationale: >
  Self-ref cap MODERATE is LIFTED to STRONG per dispatch clause
  "Deliverable A MAY reach STRONG if the critique reveals a real defect that
  platform-engineer's stub survives in its authored form". A concrete,
  reproducible path-mismatch defect on Axis 2 survives the stub as authored
  (alarms would carry 404-pointing runbook_reference tags at apply time).
  The defect is adversarially surfaced, not rubber-stamped.
verdict: REMEDIATE
verdict_scope: per-axis (not overall stub-quality)
blocking_authority: SCOPED — BLOCKING on Axis 2 (runbook path mismatch); CONCUR on Axis 1; CONCUR-WITH-CONDITIONS on Axis 3.
---

# Chaos-Engineer Sister-Specialist Critique — CW Alarms Terraform

> **Target**: `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/auth/observability/cloudwatch-alarms.tf` (406 lines, 5 alarms: 2 LIVE + 3 COMMENTED STUBs)
> **Authoring specialist**: platform-engineer (concurrent SRE session, 2026-04-22)
> **Critique style**: adversarial sister-specialist per sre-Potnia §4; not rubber-stamp
> **Verdict distribution**: CONCUR (Axis 1) | REMEDIATE (Axis 2) | CONCUR-WITH-CONDITIONS (Axis 3)

---

## §0 TL;DR

Platform-engineer's stub is structurally sound on threshold-survivability and design-decoupling rationale, but carries a **load-bearing runbook path defect** that breaks the "creating-alerts-without-runbooks" guard the author explicitly claims to honor. Five `runbook_reference` tag values point to files that **do not exist** at the claimed paths — observability-engineer authored the runbooks under a **different naming convention** in parallel. This is the canonical class of defect parallel agents produce when coordination is by "same metric topic" rather than by filename contract. Recommendation: REMEDIATE before 10x-dev consumption; do NOT merge as-authored.

---

## §1 Axis 1 — Threshold-Survivability Under Simulated Failure

### §1.1 CW-1 (revocation replay P99 > 45s) — **SURVIVES**

**Hypothesis**: Given ADR-0004 baseline of 30s budget and Postgres-baseline replay jitter 10-50ms P99, when a replay-query regression induces 50s P99, then CW-1 fires within ≤10 minutes.

**Test by construction (simulated, not executed)**:
- Injected latency: 50000ms P99 sustained
- Alarm eval: `period=300, evaluation_periods=2` → 10-min sustained window
- Comparison: `GreaterThanThreshold 45000` + `ExtendedStatistic p99`
- `treat_missing_data=notBreaching` — correctly NOT a dead-man's-switch (cold-start metric, not steady-state)

**Verdict**: `CONCUR`. The threshold is tight enough to fire at 1.5x the ADR-committed budget before the 2x breach (which would be 60s = full /internal/* outage duration). Operational buffer of 15s above the 30s budget accommodates Postgres jitter without false-positive storms. The `notBreaching` choice on missing data is semantically correct and correctly distinguished from the P6 dead-man's-switch pattern (author's inline note lines 140-141).

**Resilience note**: Platform-engineer's lines 385-388 self-document the survivability claim; it is accurate.

### §1.2 CW-3 (redirect_uri rejected spike > 10/5-min) — **SURVIVES both branches**

**Hypothesis A (attacker probing)**: 30 rejections/min sustained for 10+ min → 150/5-min-period >> 10 → fires.
**Hypothesis B (config drift)**: 15 rejections/min sustained for 10+ min → 75/5-min-period >> 10 → fires.

**Verdict**: `CONCUR`. Both failure scenarios the runbook enumerates breach the threshold with significant margin. The Sum-Statistic + `treat_missing_data=notBreaching` pairing is correct for an "emission-on-event-only" metric (zero rejections == no datapoints == healthy).

**Chaos-engineer note**: A HIDDEN failure mode the critique surfaces but does not block on — if the metric **stops emitting entirely** (code regression, log-shipping broken, CW PutMetricData 403), this alarm NEVER fires. `treat_missing_data=notBreaching` cannot distinguish "zero rejections" from "metric pipeline broken". This is not a platform-engineer defect (it is inherent to emission-on-event metrics) but **warrants a companion synthetic probe** at Phase D. Flagged as a follow-on chaos item, NOT a Wave 1 blocker.

### §1.3 CW-2a / CW-2b / CW-4 — **CHAOS-UNTESTABLE (STUB)**

Three resources are COMMENTED OUT pending 10x-dev categorization. Platform-engineer's rationale (lines 197-210, 232-239, 319-332) correctly refuses to invent a threshold without a baseline. This is **discipline, not deferral-theater** — inventing an anomaly threshold pre-baseline would produce paging-without-signal, which is exactly the alert-fatigue anti-pattern [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72 @ 2026-04-01].

**Verdict**: `CONCUR`. The decision to commit the stub as commented-out rather than provision with `threshold = 999999` (dead-code alarm) preserves the "no alert without a meaningful threshold" invariant.

**Chaos note**: Once 10x-dev activates CW-2a/2b with a concrete threshold, a second-round chaos pass MUST construct hypothesis-by-construction tests per §1.1 / §1.2. Tracking as **follow-on chaos** (post-10x-dev-merge), not a Wave 1 gap.

### §1.4 Axis 1 verdict: **CONCUR**

All three LIVE-or-commented resources survive their authored rationale. The critique cannot manufacture a threshold-survivability defect.

---

## §2 Axis 2 — Runbook_Reference Attribute Population — **DEFECT SURFACED**

### §2.1 Platform-engineer's claim

From the file preamble (lines 22-25) and lines 395-400:

> "observability-engineer authors companion runbook stubs at `autom8y/services/auth/runbooks/{alarm-name}.md` in parallel this session. Tags.runbook_reference below points to those paths; the anti-pattern guard ('Creating alerts without runbooks' — sre-Potnia standing order) is honored by the pair."

And the per-alarm tag (e.g., line 176):

```hcl
tags = merge(local.common_alarm_tags, {
  runbook_reference = "${local.runbook_base}/cw1-revocation-replay-slow.md"
})
```

Where `local.runbook_base = "autom8y/services/auth/runbooks"` (line 101).

### §2.2 Verification against observability-engineer's parallel output

**Actual files authored** at `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/`:

```
auth-oauth-device-attempts.md          (7.2k, 10:15Z)
auth-oauth-pkce-attempts.md            (6.4k, 10:15Z)
auth-oauth-redirect-uri-rejected.md    (7.8k, 10:15Z)
auth-revocation-replay-completed-ms.md (8.1k, 10:13Z)
```

**Expected files per Terraform `runbook_reference` values**:

| Alarm | Terraform-declared path | Actual file | Match |
|-------|-------------------------|-------------|-------|
| CW-1 | `autom8y/services/auth/runbooks/cw1-revocation-replay-slow.md` | `auth-revocation-replay-completed-ms.md` | **NO** (path diverges) |
| CW-2a (STUB) | `autom8y/services/auth/runbooks/cw2a-oauth-pkce-attempts.md` | `auth-oauth-pkce-attempts.md` | **NO** |
| CW-2b (STUB) | `autom8y/services/auth/runbooks/cw2b-oauth-device-attempts.md` | `auth-oauth-device-attempts.md` | **NO** |
| CW-3 | `autom8y/services/auth/runbooks/cw3-oauth-redirect-uri-rejected.md` | `auth-oauth-redirect-uri-rejected.md` | **NO** |
| CW-4 (STUB) | `autom8y/services/auth/runbooks/cw4-oauth-scope-cardinality.md` | *(file does not exist)* | **NO** |

**Defect summary**: **5 of 5** `runbook_reference` tag values point to paths that do not resolve. Two of these are on LIVE alarms that would be applied today; three are on commented STUBs that inherit the defect on activation.

### §2.3 Secondary defects surfaced during Axis 2 verification

While cross-referencing runbook content, three **semantic mismatches** were detected between Terraform and runbook text:

1. **CW numbering divergence** — Terraform assigns CW-1..CW-4; runbook H1 lines assign CW-5..CW-8:
   - `auth-revocation-replay-completed-ms.md` line 1: `# Runbook: auth.revocation.replay_completed_ms (CW-5)`
   - `auth-oauth-pkce-attempts.md` line 1: `(CW-6)`
   - `auth-oauth-device-attempts.md` line 1: `(CW-7)` (inferred; file exists, naming pattern consistent)
   - `auth-oauth-redirect-uri-rejected.md` line 1: `(CW-8)`
   - Terraform-side identifier: CW-1..CW-4 (file header "Auth OAuth + Revocation — CloudWatch Alarms (PR #131 CW-1..CW-4 BLOCKING)")
   - **Impact**: On-call engineer paged by CW-1 alarm reads "CW-5" in the runbook, breaks alarm→runbook identity.

2. **Evaluation window mismatch (CW-1)**:
   - Terraform: `period=300, evaluation_periods=2` → 10-minute sustained breach
   - Runbook (`auth-revocation-replay-completed-ms.md` line 13): "exceeds 45,000 ms (45s) over a 15-minute evaluation window"
   - **Impact**: Runbook triage-step-1 ("Confirm scope") references a dashboard window that does not match the alarm window.

3. **Threshold framing mismatch (CW-3)**:
   - Terraform: "Sum > 10 per 5-min period, 2 consecutive periods" (binary single-threshold)
   - Runbook (`auth-oauth-redirect-uri-rejected.md` line 13): "exceeds >2% of total authorize requests over a 10-minute window, OR any absolute count exceeding 100 rejections in a 5-minute window"
   - **Impact**: The runbook describes a rate-based + absolute-count alarm that is NOT what Terraform provisions. Responder triage is against a different alarm than the one that paged.

### §2.4 Root cause (chaos-engineer hypothesis)

This is the canonical defect class of **parallel-agent coordination by topic rather than by filename contract** [feedback: parallel-agent-branch-contamination; adapted to naming-contamination]. Both authors were dispatched concurrently with SRE-rite context; both knew the 4 alarm topics; neither knew the OTHER's filename convention. Platform-engineer chose `cw{N}-{metric-slug}.md` (alarm-identifier-primary); observability-engineer chose `auth-{metric-slug}.md` (service-plus-metric-primary). Both conventions are defensible in isolation; the defect is the **absence of a coordination contract** on which wins.

### §2.5 Axis 2 verdict: **REMEDIATE (BLOCKING)**

**Why BLOCKING**: The author's own file preamble (lines 398-404) states:
> "If an observability-engineer runbook is absent at 10x-dev consumption time, 10x-dev MUST either (i) author the stub or (ii) block the apply until runbook lands. Do not apply an alarm whose runbook path returns 404."

By the author's own acceptance criterion, **an alarm whose `runbook_reference` tag resolves to a non-existent path must not apply**. All 5 references violate this criterion. The author explicitly granted 10x-dev block authority; chaos-engineer exercises it pre-consumption.

**Remediation options** (pick one; 10x-dev or fleet-potnia routes):

- **Option A (Terraform-side)**: Update `runbook_reference` values in `cloudwatch-alarms.tf` to match observability-engineer's `auth-*.md` convention. Update alarm descriptions (lines 145, 268, and STUB strings 214, 237, 336) to match. Update CW-# numbering in runbook H1 headers OR update Terraform-side comments to CW-5..CW-8. Pick one numbering scheme and align both.
- **Option B (Runbook-side)**: Rename the 4 runbook files to match Terraform convention (`cw1-revocation-replay-slow.md`, etc.). Update H1 headers to match Terraform CW-1..CW-4.
- **Option C (adopt observability-engineer convention fleet-wide)**: Chaos-engineer recommendation. The `auth-{metric}.md` pattern is service-plus-metric-primary and survives alarm-renumbering over time (CW-numbering is sprint-local; metric-name is permanent). Update Terraform to match.

Additionally, create `auth-oauth-scope-cardinality.md` (CW-4/CW-9 runbook) OR remove the reference from the CW-4 stub until the runbook exists. Current state: CW-4 stub promises a runbook that was never authored.

**Deliverable**: 10x-dev (or fleet-potnia at Phase B/C routing) produces a **runbook-path reconciliation patch** touching both the Terraform file and the 4 (or 5) runbook files before any apply.

---

## §3 Axis 3 — Non-Obvious Design Decisions Validation

### §3.1 CW-2 split into CW-2a (PKCE) + CW-2b (Device) — **VALIDATE**

**Author's rationale** (lines 219-229):
> "Separate alarm from PKCE because the two flows have independent consumer populations — unifying them would mask failures in one population under healthy activity of the other."

**Chaos-engineer evaluation**:

The rationale invokes a population-separability principle. Steel-man test: is there a failure mode where unified CW-2 masks a population-specific failure that separated CW-2a/2b would catch?

**Yes**. Concrete scenario:
- PKCE consumers: admin-CLI (human operators, bursty traffic, ~10 authorize/hr/operator, ~20 active operators → ~200 /hr fleet-wide)
- Device consumers: M2M service-accounts (steady traffic, ~1 authorize/min/SA, ~10 SAs → ~600/hr fleet-wide)
- Failure mode: admin-CLI's PKCE challenge generator regresses to malformed base64url (observability-engineer's PKCE runbook hypothesis 2, "client regression"). PKCE attempts drop to 0.
- Unified metric: 0 (admin-CLI) + 600 (M2M healthy) = 600/hr — indistinguishable from baseline (~800/hr). **Masked.**
- Separated metric: CW-2a goes to 0, CW-2b steady. **Detected** via dead-man's-switch on CW-2a (Variant A).

**Population-mixing masks population-specific failures** — this is the standard argument for segmentation-by-consumer-population [SR:SRC-007 Majors, Fong-Jones & Miranda 2022] [MODERATE | 0.72 @ 2026-04-01]. The author's decoupling decision is correct.

**Verdict**: `CONCUR`. The split is not theater; it is load-bearing for the PKCE-specific failure mode.

### §3.2 Three open-questions for 10x-dev — **TRIAGE**

Author lines 44-55, 197-210, 319-332 enumerate three 10x-dev-owned decisions. Chaos-engineer triages each for SRE-rite resolvability:

#### §3.2.1 File location shape (lines 44-55)

Options (a) promote to child-module with inputs, vs (b) move up to sibling of `token_exchange_alarms.tf`.

**Triage**: **Genuinely 10x-dev-owned**. This is a Terraform-module-architecture decision depending on where else `observability/` might expand. SRE rite has no authority to prefer (a) vs (b); either survives the chaos criteria.

**Verdict**: `CONCUR` with deferral. No SRE-rite action.

#### §3.2.2 CW-2a/2b dashboard-only vs anomaly-alarm (lines 197-210)

Options (A) dashboard-only (no alarm), (B) post-baseline anomaly at `mean + 3*stddev` over 15-min.

**Triage**: **SRE-rite SHOULD weigh in**, not leave purely to 10x-dev. Chaos-engineer preference:

- Option (A) + companion Option (B) staged at T+7d. Start dashboard-only at merge; calibrate baseline for 7 days; promote to anomaly alarm at T+7 with `mean + 3*stddev`. This is the observability-engineering standard for anomaly thresholding from no prior [SR:SRC-007] [MODERATE | 0.72 @ 2026-04-01].
- Option (B) straight-away without a baseline period would fire on Day-0 based on assumed-mean-of-zero, which is the "alert-fatigue from uncalibrated threshold" anti-pattern [SR:SRC-001 Beyer et al. 2016].

**Verdict**: `CONCUR-WITH-CONDITIONS`. SRE rite SHOULD contribute an opinion here even though 10x-dev holds final decision. Chaos-engineer recommends **(A) at merge → (B) at T+7d** and flags this for incident-commander sign-off in the Wave 1 HANDOFF-RESPONSE.

#### §3.2.3 CW-4 emission wiring — companion gauge vs log-metric-filter (lines 319-332)

Options (A) emit `ScopeCardinalityObserved` gauge metric (requires code change), (B) CloudWatch Logs metric-filter on existing WARNING log (no code change).

**Triage**: **Genuinely 10x-dev-owned**. The decision depends on (1) code-velocity tolerance at 10x-dev (how quickly can they add the gauge emission), and (2) log-shape stability (is `token_exchange_cw_metrics_scope_cardinality_overflow` WARNING log-string permanent or about to refactor). Neither is SRE-visible.

**Chaos note**: Option (B) is lower-code-change-cost but introduces a cross-cutting fragility — a future log-format refactor silently breaks the metric-filter with no test coverage. Option (A) is more durable. If 10x-dev prefers (B), a **log-shape-stability test** should be added under 10x-dev ownership.

**Verdict**: `CONCUR` with deferral + chaos-footnote. No SRE-rite block.

### §3.3 Axis 3 verdict: **CONCUR-WITH-CONDITIONS**

- Design-decoupling (CW-2a/2b split): CONCUR
- Open-question triage: 2/3 genuinely 10x-dev-owned; 1/3 (CW-2a/2b framing) SRE-rite should weigh in. Condition: incident-commander or observability-engineer emits an opinion on (A) dashboard-only at merge + (B) anomaly at T+7d, included in HANDOFF-RESPONSE.

---

## §4 Overall Verdict: **REMEDIATE** (scoped to Axis 2)

| Axis | Verdict | Evidence Grade | Block-Class |
|------|---------|----------------|-------------|
| 1. Threshold-survivability | CONCUR | STRONG (simulated-by-construction) | none |
| 2. Runbook_reference population | **REMEDIATE (BLOCKING)** | **STRONG** (5/5 concrete path mismatches verified via filesystem) | **pre-10x-dev-consumption** |
| 3. Non-obvious design decisions | CONCUR-WITH-CONDITIONS | MODERATE | soft (condition: SRE input on CW-2a/2b framing) |

**Overall**: REMEDIATE. The stub does NOT ship to 10x-dev consumption as-authored. The Axis 2 defect is objectively verifiable, author-acknowledged as a blocking class in their own file preamble, and fixable in a single reconciliation patch touching 2 files (or 6, depending on Option A/B/C).

---

## §5 Resilience Scorecard

| Category | Score | Note |
|----------|-------|------|
| Hypothesis-driven design | PASS | Every alarm has inline blast_radius + failure-mode + rollback-safety documented |
| Blast-radius containment | PASS | ADR-0006 two-tower invariant preserved; each alarm scoped to ONE plane |
| Abort criteria (per-alarm) | PASS | `treat_missing_data` semantics explicitly chosen per metric; notBreaching vs breaching decision documented |
| Compound-fault readiness | **PARTIAL** | CW-3 emission-pipeline-silence is a compound-fault not alarmed by CW-3 itself. Follow-on item for Phase D chaos. |
| Runbook pairing | **FAIL** | 5/5 path references broken. Anti-pattern guard claimed-but-not-enforced. |
| Coordination-by-contract | **FAIL** | Parallel agents chose divergent filename conventions. No pre-agreed contract. Process-level defect, not individual author defect. |

---

## §6 Recommendations (priority-ordered)

### P0 — BLOCKING (pre-10x-dev-consumption)
1. **Reconcile runbook paths**. Pick Option A/B/C from §2.5. Chaos preference: Option C (`auth-{metric}.md` fleet-wide, update Terraform to match). Touch: `cloudwatch-alarms.tf` (5 tag values + 5 alarm_description strings) + runbook H1 lines (update CW-# to consistent scheme).
2. **Create CW-4 runbook** OR remove the `runbook_reference` from CW-4 STUB until runbook is authored. Do not ship a STUB promising a non-existent file.
3. **Fix CW-1 evaluation-window mismatch** (Terraform 10-min vs runbook 15-min text). Align runbook text to Terraform or vice-versa.
4. **Fix CW-3 threshold-framing mismatch** (Terraform binary-absolute vs runbook rate-plus-absolute). Align.

### P1 — HIGH (for HANDOFF-RESPONSE completeness)
5. **SRE opinion on CW-2a/2b dashboard-first → anomaly-at-T+7d**. Incident-commander or observability-engineer emits 1-paragraph recommendation.
6. **Coordination-contract process fix**: future parallel agent dispatches should include a pre-agreed filename contract in the HANDOFF packet. Route to sre-Potnia as a retrospective finding.

### P2 — MEDIUM (follow-on chaos)
7. **CW-3 emission-pipeline synthetic probe** (Phase D). Alarm on "metric emits SOMETHING every 15 minutes in prod" to catch the "metric pipeline broken" failure mode that `treat_missing_data=notBreaching` cannot distinguish.
8. **CW-1 cold-start frequency baseline**. Measure cold-start rate for 7d post-merge; if rate is low enough that `period=300, eval=2` rarely collects enough samples, revise to `period=60, eval=10` (1-min granularity, 10-min window).
9. **CW-4 log-shape-stability test** (if 10x-dev picks emission-wiring Option B). Add a test that asserts the WARNING log-string constant does not drift.

---

## §7 Coordination Notes for Fleet-Potnia

- This critique is **in-rite adversarial** (chaos-engineer vs platform-engineer, same SRE rite). Evidence grade caps at STRONG because a concrete reproducible defect was surfaced, but external-rite corroboration (e.g., hygiene 11-check) would strengthen it further.
- The Axis 2 defect is a **parallel-agent coordination pattern**, not an individual-author defect. Platform-engineer acted correctly under the constraint of not knowing observability-engineer's filename choice. The process-level recommendation (P1 #6) is the durable fix.
- 10x-dev consumption SHOULD be deferred until P0 items 1-4 land. A single reconciliation patch covers all four.

---

## §8 Appendix — Verification evidence (reproducible)

```
# Runbook directory listing (ground truth)
$ ls /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/ | grep -E '(oauth|revocation|cw[1-4])'
auth-oauth-device-attempts.md
auth-oauth-pkce-attempts.md
auth-oauth-redirect-uri-rejected.md
auth-revocation-replay-completed-ms.md

# Terraform runbook_reference tag values
$ grep 'runbook_reference' cloudwatch-alarms.tf
    runbook_reference = "${local.runbook_base}/cw1-revocation-replay-slow.md"          (line 176 — LIVE)
#     runbook_reference = "${local.runbook_base}/cw2a-oauth-pkce-attempts.md"          (STUB, referenced in alarm_description)
#     runbook_reference = "${local.runbook_base}/cw2b-oauth-device-attempts.md"        (STUB)
    runbook_reference = "${local.runbook_base}/cw3-oauth-redirect-uri-rejected.md"     (line 296 — LIVE)
#     runbook_reference = "${local.runbook_base}/cw4-oauth-scope-cardinality.md"       (STUB, line 360)

# Runbook H1 CW-numbering
$ head -1 /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-revocation-replay-completed-ms.md
# Runbook: `auth.revocation.replay_completed_ms` (CW-5)
$ head -1 /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-pkce-attempts.md
# Runbook: `auth.oauth.pkce.attempts` (CW-6)
$ head -1 /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-redirect-uri-rejected.md
# Runbook: `auth.oauth.redirect_uri.rejected` (CW-8)

# Evaluation-window mismatch (CW-1)
Terraform:  period=300, evaluation_periods=2  →  10-min sustained
Runbook:    "over a 15-minute evaluation window"  (auth-revocation-replay-completed-ms.md line 13)

# Threshold-framing mismatch (CW-3)
Terraform:  Sum > 10 per 5-min, 2 consecutive periods  (binary absolute)
Runbook:    ">2% of total authorize requests over a 10-minute window, OR any absolute count exceeding 100 rejections in a 5-minute window"
            (auth-oauth-redirect-uri-rejected.md line 13)
```

---

**End chaos-engineer critique. Verdict: REMEDIATE (Axis 2 BLOCKING) — do not consume at 10x-dev until P0 items 1-4 land.**
