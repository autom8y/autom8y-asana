---
# ============================================================================
# Cross-Rite HANDOFF — 10x-dev (architect) → monorepo operator (autom8y/autom8y)
# Two IaC invariants the asana repo CANNOT apply (zero .tf in-repo); operator
# carries this to the autom8y MONOREPO and applies there.
# ============================================================================
# Schema: cross-rite-handoff v1.0 (handoff_type: execution — acceptance_criteria per item)
artifact_id: HANDOFF-10x-dev-to-monorepo-cpumem-floor-and-vg005-alarm-2026-06-08
schema_version: "1.0"
type: handoff
status: draft
handoff_type: execution
source_rite: 10x-dev
target_rite: monorepo-operator          # autom8y/autom8y IaC owner (no rite; carries to TF)
priority: high
blocking: false                         # regression-prevention + paging; not gating an active deploy
initiative: "RECV-BULK-001 substrate hardening — cpu/mem floor (P0-a) + VG-005 CPU-starvation alarm (P2-b)"
date: 2026-06-08
created_at: "2026-06-08T00:00:00Z"
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
related_repos:
  - autom8y/autom8y                     # APPLY TARGET — all .tf lives here
  - autom8y/autom8y-asana               # SOURCE of invariant intent; zero .tf (verified)
monorepo_targets:
  - "asana/main.tf:144-159 (cpu/mem task-def registration) — P0-a floor"
  - "asana/<alarms>.tf (CloudWatch alarm module for the asana service) — P2-b VG-005 alarm"
source_artifacts:
  - src/autom8_asana/settings.py:295-303          # in-repo floor-intent anchor comment
  - src/autom8_asana/cache/dataframe/build_coordinator.py:136-143   # in-repo floor-intent anchor comment
  - src/autom8_asana/api/metrics.py:550-577        # receiver-side cpu_starvation_precondition helper
  - .know/obs.md:32                                # "asana has 0 .tf" claim
acceptance_criteria:
  P0-a:
    - "cpu < 2048 OR mem < 8192 is UN-REGISTERABLE: a plan/apply attempting a sub-floor task-def fails CLOSED (error at plan or CI assert), not silently."
    - "A CI-writer race re-introducing cpu=256 (the rev454/455/456 historical regression) is rejected by the guard before apply."
  P2-b:
    - "A CloudWatch alarm exists in the asana service .tf that transitions to ALARM on the CPU-starvation-replacement signature and routes to the paging SNS topic (PagerDuty), not email-only."
    - "The alarm references the same two external signals (alb_unhealthy_host_count + ecs_task_replacement_count) the receiver-side precondition helper correlates."
# ---------------------------------------------------------------------------
# Verification posture (SVR discipline): in-repo anchors were directly inspected
# at authoring time. Monorepo .tf state (rev numbers, current cpu/mem values) is
# NOT inspectable from this repo (zero .tf) — those claims carry UV-P labels and
# are the operator's FIRST step to confirm. See §0.
# ---------------------------------------------------------------------------
---

# HANDOFF: 10x-dev (architect) → monorepo operator — cpu/mem FLOOR (P0-a) + VG-005 alarm (P2-b)

## §0 — G-RUNG boundary + verification posture (read first)

This handoff is **authored, not applied**. The architect does NOT touch any `.tf` and
does NOT apply to the monorepo. The asana repo has **zero `.tf` files** — verified at
authoring time by `find . -name "*.tf" -not -path "*/.venv/*"` → count `0`
(corroborated by `.know/obs.md:32`: "asana has 0 `.tf`"). Both invariants below land in
the **autom8y MONOREPO** (`autom8y/autom8y`). The operator carries this doc there and applies.

**Directly inspected at authoring time (this repo, file-read receipts):**

- `src/autom8_asana/settings.py:295-303` — verbatim slice: *"exceeds the current ECS task sizing (cpu=1024 / mem=2048 -> ~768 MB usable after the 256-unit ADOT sidecar reservation; autom8y .../asana/main.tf:144-159)"*. This is the in-repo declaration that the floor lever is INERT and DANGEROUS to raise without a prior task bump.
- `src/autom8_asana/cache/dataframe/build_coordinator.py:136-143` — verbatim slice: *"(cpu=1024 / mem=2048, ~768MB usable after the 256-unit ADOT sidecar; autom8y .../asana/main.tf:144-159). The lever is INERT and DANGEROUS to raise without first verifying a CPU/mem task bump."*
- `src/autom8_asana/api/metrics.py:550-577` — `cpu_starvation_precondition(event_loop_lag_seconds, cpu_thread_semaphore_waiting) -> bool`; docstring at metrics.py:561-562 names the two external confirming signals *"alb_unhealthy_host_count rising + ecs_task_replacement_count increment"*; the external-signal pair is also named at metrics.py:543-544.

**NOT inspectable from this repo — operator must confirm in the monorepo FIRST (UV-P):**

- `[UV-P: asana/main.tf:144-159 currently registers cpu=2048/mem=8192 on revs :480-485 (clean) | METHOD: deferred-to-operator-tf-read | REASON: zero .tf in asana repo; monorepo state not inspectable here. NOTE the in-repo anchor comments (settings.py:298, build_coordinator.py:139) describe the task as cpu=1024/mem=2048 — that text may be STALE relative to the :480-485 revs the pickup map calls clean. The operator MUST read the live main.tf:144-159 before choosing the floor mechanism, because the guard value depends on what the current registration actually is.]`
- `[UV-P: a CI-writer race historically re-registered cpu=256 at revs rev454/455/456 | METHOD: deferred-to-operator-tf-history | REASON: revision history lives in the monorepo TF state / CI logs, not here. Confirm via `aws ecs list-task-definitions --family <asana-family>` + describe, or TF state history, before sizing the CI assert.]`

If the operator's read of live `main.tf:144-159` contradicts either UV-P (e.g. current value is NOT 2048/8192), STOP and re-scope — the floor value below assumes 2048/8192 is the ratified clean target.

> **UV-P #1 CORROBORATED by main-thread live AWS verify (2026-06-08, post-authoring).** A direct
> `ecs describe-task-definition` on the running `autom8y-asana-service` confirmed task-def **`:485` =
> cpu=2048 / mem=8192**, and revs **`:480`–`:485` are ALL cpu=2048/mem=8192** (no cpu=256 in recent
> history). So the floor target (cpu≥2048 AND mem≥8192) matches the LIVE registration; the in-repo
> `1024/2048` anchor comments ARE stale (pre-§D vertical scale). The operator should still re-read
> `main.tf:144-159` at apply time (state can move), but the 2048/8192 target is live-confirmed, not
> assumed. Receipt: `.ledge/reviews/cr3-r3-gate2-producer-pickup-map-2026-06-07.md` §A + the
> probe receipt `cr3-r3-gate2-receiver-probe-receipt-2026-06-08.md`.

---

## §1 — P0-a: cpu/mem FLOOR invariant (autom8y monorepo, `asana/main.tf:144-159`)

### Problem

The cpu/mem task-def registration for the asana service is the substrate ceiling for the
inline DataFrame-build concurrency lever (`dataframe_max_concurrent_builds`, default 4).
The in-repo anchors (settings.py:295-303, build_coordinator.py:136-143) document that
raising concurrency above 4 requires a verified CPU/mem bump first — i.e. the task sizing
is **load-bearing for RECV-BULK-001 reliability**. A CI-writer race historically
re-registered `cpu=256` (rev454/455/456 per the pickup map; UV-P above). Recent revs
:480-485 are clean at `cpu=2048/mem=8192` (UV-P above) — but **nothing structurally
prevents regression**. The next CI-writer race, stale-tfvars merge, or hand-edit can
silently drop the task back below the floor, and the single-worker receiver starves under
bulk fan-out (the RECV-BULK-001 failure signature).

### Invariant (precise)

> **`cpu >= 2048` AND `mem >= 8192` MUST be un-registerable below.** Any plan/apply that
> would register the asana task-def with `cpu < 2048` or `mem < 8192` MUST fail CLOSED —
> at `terraform plan` (preferred) or at a CI assert gate (backstop) — never apply silently.

This is a **one-way-door reversibility note**: tightening a floor is a two-way door (relax
later if capacity work proves it unneeded), but the *absence* of a floor is the regression
vector. The floor is cheap to add and cheap to relax; the cost of NOT having it is a silent
sub-floor re-registration that pages on-call. Add the floor.

### Exact change shape — three options, with tradeoffs

The operator picks ONE. **Recommended: Option A** (plan-time, fail-closed, in the same
module as the value — closest to the resource, hardest to bypass).

**Option A — Terraform variable `validation` block (plan-time, fail-closed) [RECOMMENDED]**

Make cpu/mem inputs to `asana/main.tf:144-159` flow through variables carrying a
`validation` block:

```hcl
variable "asana_task_cpu" {
  type    = number
  default = 2048
  validation {
    condition     = var.asana_task_cpu >= 2048
    error_message = "FLOOR VIOLATION: asana_task_cpu must be >= 2048 (RECV-BULK-001 substrate floor; see HANDOFF-...-cpumem-floor-2026-06-08). Sub-floor re-registration starves the single-worker receiver under bulk fan-out."
  }
}

variable "asana_task_memory" {
  type    = number
  default = 8192
  validation {
    condition     = var.asana_task_memory >= 8192
    error_message = "FLOOR VIOLATION: asana_task_memory must be >= 8192 (RECV-BULK-001 substrate floor)."
  }
}
```

The `aws_ecs_task_definition` at `main.tf:144-159` then references `var.asana_task_cpu` /
`var.asana_task_memory`. Any value below the floor fails at `terraform plan` with a named
error — the CI-writer race cannot produce an applyable plan.

- **Pro**: Fails CLOSED at plan time, BEFORE apply. In-module — no extra CI wiring, no drift between the guard and the resource. The error message is self-documenting at the failure site. Native Terraform; no extra tooling.
- **Con**: Only guards values that flow through the *variable*. If a future edit hardcodes a literal in the resource block (bypassing the variable), the validation does not see it. Mitigate with a one-line `lifecycle` precondition (Option B) co-located on the resource as belt-and-suspenders, OR a CI grep assert (Option C) that the resource references the variable.

**Option B — `lifecycle { precondition }` on the resource (plan/apply-time, fail-closed)**

Attach a precondition directly to the `aws_ecs_task_definition` resource at `main.tf:144-159`:

```hcl
resource "aws_ecs_task_definition" "asana" {
  cpu    = ...
  memory = ...
  # ... main.tf:144-159 ...
  lifecycle {
    precondition {
      condition     = tonumber(self.cpu) >= 2048 && tonumber(self.memory) >= 8192
      error_message = "FLOOR VIOLATION: asana task-def cpu>=2048 && mem>=8192 required (RECV-BULK-001 substrate floor)."
    }
  }
}
```

- **Pro**: Guards the **resolved resource value** regardless of whether it came from a variable, a literal, or a `tfvars` merge — closes Option A's literal-bypass gap. Co-located on the resource.
- **Con**: `self.*` preconditions evaluate during plan for known values but can defer to apply for values not known until apply — slightly later failure surface than a pure variable validation. Use Option A + Option B together for both surfaces (variable-input AND resolved-resource).

**Option C — `tfvars` min-guard + CI assertion (backstop, fail-closed at CI)**

Keep the floor as a documented `tfvars` minimum and add a CI step that asserts the
registered/planned values:

```bash
# CI gate: parse `terraform plan -json` (or describe the rendered task-def) and fail the build
PLAN_CPU=$(terraform show -json plan.out | jq -r '... aws_ecs_task_definition.asana ... .cpu')
PLAN_MEM=$(terraform show -json plan.out | jq -r '... .memory')
if [ "$PLAN_CPU" -lt 2048 ] || [ "$PLAN_MEM" -lt 8192 ]; then
  echo "FLOOR VIOLATION: planned asana task-def cpu=$PLAN_CPU mem=$PLAN_MEM below floor 2048/8192"; exit 1
fi
```

- **Pro**: Catches ANY path to a sub-floor value, including out-of-band hand-edits and the original CI-writer race, because it asserts on the rendered plan. Repo-agnostic to how the value is set.
- **Con**: Fails at CI, not at `terraform plan` on a developer's machine — later in the loop. Adds CI surface to maintain (jq path is brittle to module-address changes). It is a BACKSTOP, not the primary guard.

### Recommended composite

**A (variable validation) as the primary plan-time floor + C (CI plan-json assert) as the
race-proof backstop.** A makes the common path fail-closed early and self-documenting; C
catches the literal-bypass and out-of-band edit that A alone misses, which is precisely the
CI-writer-race vector that produced rev454/455/456. B is optional belt-and-suspenders if the
resource ever takes literals. This is the canonical "fail at plan + assert at CI" defense for
a value that has *already regressed once via a race*.

### Acceptance (P0-a)

- A `terraform plan` with `asana_task_cpu = 256` (or any sub-floor cpu/mem) fails with the named FLOOR VIOLATION error — verified by the operator running it once as a negative test.
- The CI assert rejects a rendered plan with sub-floor cpu/mem.

---

## §2 — P2-b: VG-005 CPU_STARVATION_REPLACEMENT alarm (autom8y monorepo, asana service `.tf`)

### Problem

The receiver-side precondition helper for the CPU-starvation-replacement signature already
EXISTS in-repo at `src/autom8_asana/api/metrics.py:550-577`
(`cpu_starvation_precondition`). It evaluates the **two receiver-observable leading
signals** (event-loop lag > 500ms AND CPU-thread offload semaphore saturated) and returns
True as the receiver's *contribution* to a four-signal correlation. The design (metrics.py
docstring 555-573) states the **two EXTERNAL confirming signals** —
`alb_unhealthy_host_count` rising + `ecs_task_replacement_count` increment — are correlated
from CloudWatch by the re-gate stream, and that the receiver "does NOT self-declare the full
classification." **Today there is no CloudWatch alarm that fires on this signature**, so a
RECV-BULK-001 CPU-starvation regression (task replaced under bulk fan-out load) does NOT
PAGE — it is silent until a human notices degraded fan-out.

### Invariant (precise)

> A CloudWatch alarm in the asana service `.tf` MUST transition to `ALARM` on the
> CPU-starvation-replacement signature — the **co-occurrence of ALB unhealthy hosts AND an
> ECS task replacement** within a short window — and MUST route to the **paging** SNS topic
> so the regression PAGES on-call (not email-only, not dashboard-only).

The alarm is the EXTERNAL half of the four-signal correlation made operational; the receiver
already emits the leading half. The external pair is exactly the signal the in-repo helper
defers to CloudWatch (metrics.py:543-544, 561-562).

### Specified alarm

Because the signature is a **correlation of two metrics** (unhealthy host AND task
replacement), use a CloudWatch **metric-math / composite** construction. Two equivalent
shapes; pick per the module's existing alarm idiom.

**Shape 1 — single `aws_cloudwatch_metric_alarm` with metric-math expression (RECOMMENDED)**

```hcl
resource "aws_cloudwatch_metric_alarm" "asana_cpu_starvation_replacement" {
  alarm_name        = "asana-VG-005-CPU_STARVATION_REPLACEMENT"
  alarm_description  = <<-EOT
    RECV-BULK-001 CPU-starvation-replacement signature: ALB unhealthy hosts co-occurring
    with an ECS task replacement. Receiver-side leading signals
    (event-loop lag >500ms + CPU offload-semaphore saturation) are emitted by
    cpu_starvation_precondition() at asana api/metrics.py:550-577; this alarm confirms the
    two EXTERNAL signals (alb_unhealthy_host_count + ecs_task_replacement_count) per the
    design at metrics.py:543-544,561-562. Page on-call.
  EOT

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1                # signature present (math expr returns 1 on co-occurrence)
  evaluation_periods  = 2                # datapoints to evaluate
  datapoints_to_alarm = 2                # 2-of-2: require sustained co-occurrence, suppress single-scrape blips
  period              = 60               # 1-min granularity on each metric (set per metric below)
  treat_missing_data  = "notBreaching"   # missing != starvation; do NOT page on metric gaps

  # m1: ALB unhealthy host count for the asana target group (>=1 host unhealthy)
  metric_query {
    id          = "m1"
    return_data = false
    metric {
      metric_name = "UnHealthyHostCount"          # ALB/TargetGroup; mirrors alb_unhealthy_host_count
      namespace   = "AWS/ApplicationELB"
      period      = 60
      stat        = "Maximum"
      dimensions  = { TargetGroup = "<asana-tg-arn-suffix>", LoadBalancer = "<asana-alb-arn-suffix>" }
    }
  }

  # m2: ECS task replacement signal for the asana service.
  # Prefer a custom emitted metric mirroring ecs_task_replacement_count if published;
  # otherwise derive from a service-deployment / running-task-count drop. See note below.
  metric_query {
    id          = "m2"
    return_data = false
    metric {
      metric_name = "ecs_task_replacement_count"  # custom ns if emitted; else see derivation note
      namespace   = "Autom8y/Asana"
      period      = 60
      stat        = "Sum"
      dimensions  = { Service = "asana" }
    }
  }

  # Signature = both present in the same window: unhealthy host AND a replacement.
  metric_query {
    id          = "sig"
    expression  = "IF(m1 >= 1 AND m2 >= 1, 1, 0)"
    label       = "cpu_starvation_replacement_signature"
    return_data = true
  }

  alarm_actions = [var.asana_paging_sns_topic_arn]   # PagerDuty-backed; NOT email-only
  ok_actions    = [var.asana_paging_sns_topic_arn]
}
```

**Parameter rationale (the floor the operator must not soften):**

| Param | Value | Why |
|-------|-------|-----|
| metric m1 | `AWS/ApplicationELB UnHealthyHostCount` (Max), asana TG | The `alb_unhealthy_host_count` external signal named at metrics.py:543,561. Max stat: any unhealthy host in the window counts. |
| metric m2 | `ecs_task_replacement_count` (Sum), asana service | The `ecs_task_replacement_count` external signal named at metrics.py:544,562. Sum: count replacements in the window. |
| expression | `IF(m1>=1 AND m2>=1, 1, 0)` | The CORRELATION — the signature is co-occurrence, not either signal alone. Either alone is noisy (a deploy replaces tasks; a slow target trips unhealthy); together they are the starvation-replacement signature. |
| threshold | `>= 1` | Math expr returns 1 only when the signature holds. |
| period | `60s` | 1-min granularity matches the receiver's window altitude; starvation manifests in seconds-to-minutes. |
| evaluation_periods / datapoints_to_alarm | `2 / 2` | 2-of-2 sustained: suppresses a single-scrape blip / one-off deploy-time replacement, still pages within ~2 min of a real starvation-replacement. |
| treat_missing_data | `notBreaching` | A metric gap is NOT starvation; do not page on missing data (avoids false pages during scrape gaps). |
| alarm_actions | paging SNS (PagerDuty) | DoD = "regressions PAGE." Email/dashboard-only fails the invariant. |

**m2 derivation note (operator decision):** if `ecs_task_replacement_count` is not yet
published as a custom CloudWatch metric, derive the replacement signal from an
ECS-native proxy in the same window — e.g. a drop in `RunningTaskCount` /
`DesiredvsRunning` divergence, or a `DeploymentCount`/service-event-driven metric — OR
publish the custom metric to close the gap to the in-repo helper's named signal. Deriving
from a deploy-only signal risks false correlation during normal deploys; prefer publishing
the explicit replacement counter so the alarm references the SAME signal the receiver helper
names. Flag this as the one open implementation choice.

**Shape 2 — two simple alarms + `aws_cloudwatch_composite_alarm`** (if the module avoids
metric-math): one alarm on `UnHealthyHostCount >= 1`, one on the replacement metric `>= 1`,
combined with `ALARM(unhealthy) AND ALARM(replacement)` in a composite alarm whose actions
page. Equivalent semantics; more resources, clearer per-signal state in the console. Same
2-of-2 / period / paging-SNS parameters apply to the leaf alarms.

### Acceptance (P2-b)

- The alarm transitions to `ALARM` only when BOTH `alb_unhealthy_host_count`-equivalent AND `ecs_task_replacement_count`-equivalent are present in the same evaluation window (verified by the operator with a synthetic datapoint test or by inspecting a past RECV-BULK-001 incident window).
- `alarm_actions` route to the PagerDuty-backed paging SNS topic — a fired alarm PAGES.
- The alarm description references `api/metrics.py:550-577` so the on-call responder can trace from the page to the receiver-side leading signals.

---

## §3 — Operator runbook (apply order)

1. **Confirm the two UV-P claims** (§0): read live `asana/main.tf:144-159` for current cpu/mem; confirm the rev454/455/456 regression + :480-485 clean state from TF state / ECS task-def history. If live ≠ 2048/8192, STOP and re-scope the floor value with the architect.
2. **P0-a**: add Option A variable validations referencing main.tf:144-159 + Option C CI plan-json assert. Run a negative test (`asana_task_cpu = 256` → plan fails). Apply.
3. **P2-b**: add the metric-math alarm (Shape 1) wired to the asana paging SNS topic. Confirm m1/m2 metric names + dimensions against the live asana TG/ALB/service; resolve the m2 derivation note. Apply.
4. **Attest back**: record applied rev + alarm ARN in a return handoff or in `.know/obs.md` so the asana repo's observability ledger reflects that OBS residuals (cpu/mem floor + VG-005) are now LANDED in the monorepo.

---

## §4 — Out of scope / non-goals

- The architect does NOT apply to the monorepo and does NOT edit any `.tf` (G-RUNG: authored ≠ applied).
- No change to `dataframe_max_concurrent_builds` / `max_concurrent_builds` (still 4) — this handoff secures the SUBSTRATE floor, not the concurrency lever. Raising the lever remains OQ-1-gated per settings.py:300-303.
- No change to the receiver-side helper (metrics.py:550-577) — it is correct as-is; this handoff operationalizes the external half it already defers to CloudWatch.
