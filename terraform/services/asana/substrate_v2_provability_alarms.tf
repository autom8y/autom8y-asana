# ============================================================================
# substrate-v2 provability alarm suite (PROV-1 .. PROV-6) — RC-F
# ============================================================================
#
# AUTHORED wave-2; APPLY = DP-4a (operator door); this repo has no apply
# pipeline (see observability_alarms.SURFACED.md).
#
# Source of truth: .ledge/specs/TDD-substrate-v2.md §4 Seam 5 + §3 RC-F
#                  (F6 RATIFIED-AUTO; C7/C10 folded).
#
# SAME-MODULE NOTE: this file co-resides with observability_alarms.tf (one
# Terraform module = one directory). It REUSES that file's `terraform{}` provider
# block, its master paging kill-switch variables (`arm_paging`,
# `paging_armed_alarms`, `page_sns_topic_arn`, `ticket_sns_topic_arn`,
# `environment`) and its `local.page_action` / `local.ticket_action` wiring — so
# ONE master switch governs both suites. This file ADDS only substrate-v2
# variables, the PROV-1..6 alarms, their action locals, and their outputs.
# Operators arm a PROV alarm by adding e.g. "PROV-1" to `paging_armed_alarms`.
#
# WHAT THIS CURES (vs the AL-5 precedent one file over):
#   AL-5 watches OfferFrameAgeSeconds, a log-metric emitted ONLY when a frame is
#   SERVED (queried). A registered-but-unqueried GID emits no datapoint, so AL-5
#   runs treat_missing_data=notBreaching and carries an ACKNOWLEDGED blind spot
#   (a starved-AND-unqueried GID is invisible). The orphaned
#   `autom8-asana-cache-warmer-DMS-24h` is the same failure class worse: a
#   dead-man watching a now-EMPTY namespace — a dead-man on a dead metric.
#
#   RC-F removes the query dependency. A SCHEDULED evaluator (EventBridge->Lambda
#   / warmer post-step, [H22]) evaluates EVERY expected artifact through the SAME
#   is_provable the serve gate uses ([H19]) and emits on EVERY run — so these
#   alarms watch DENSE metrics that EXIST whether or not anything is queried. The
#   heartbeat (PROV-2) is therefore the dead-man DONE RIGHT: a no-data alarm on a
#   metric that is present on every healthy run, so the evaluator's own silence is
#   a breach rather than an unnoticed gap.
#
# STATUS: AUTHORED / UN-DEPLOYED / UN-ARMED.
#   - NOT wired into any apply pipeline by this change (the live apply lane is
#     cross-repo; see observability_alarms.SURFACED.md + the DP-4a door note).
#   - Every alarm is authored WITHOUT an SNS/pager action by default (inherits the
#     shared arm_paging=false + paging_armed_alarms=[] safe defaults).
#   - Arming a PROV alarm is a confirm-first operator action (DP-4a).
#
# Rung discipline: the ProvabilityEvaluator + its emission are built DARK this
# sprint (no deploy). These metrics are `emitting-in-fixtures`, NOT `proven` in
# prod. C10 (CARRY-TO-BUILD): the cutover gate's evidence must include ONE
# observed end-to-end FIRED alarm (synthetic unprovability -> operator-visible
# notification); that firing is DEFERRED to S8 (potnia ruling), not this file.
# ============================================================================

# ----------------------------------------------------------------------------
# Variables -- substrate-v2 additions only (shared paging vars live in
# observability_alarms.tf; re-declaring them is a same-module collision).
# ----------------------------------------------------------------------------

variable "substrate_provability_namespace" {
  description = <<-EOT
    CloudWatch namespace the ProvabilityEvaluator emits to. MUST match
    `substrate.observe.SUBSTRATE_PROVABILITY_NAMESPACE` verbatim -- a rename on
    either side silently un-wires these alarms.
  EOT
  type        = string
  default     = "Autom8y/SubstrateProvability"
}

variable "evaluation_schedule_seconds" {
  description = <<-EOT
    The evaluator's scheduled cadence (seconds). Drives the PROV-1/3/4 alarm
    period: because RC-F emission is DENSE (every scheduled run, query-independent),
    a datapoint lands each cadence -- no M-of-N sparsity cure is needed here
    (contrast AL-5's 2-of-12 config, forced by query-gated sparse emission).
  EOT
  type        = number
  default     = 900 # 15 minutes
}

variable "heartbeat_deadman_period_seconds" {
  description = <<-EOT
    PROV-2 dead-man window (seconds). At the 900s default cadence this expects
    >= 4 heartbeats/hour; a window with < 1 heartbeat (or none at all) breaches.
    The dead-man is DONE RIGHT: it watches EvaluatorHeartbeat, a metric present on
    every healthy run, so the evaluator's own absence is a breach (not an
    unnoticed gap on an empty namespace).
  EOT
  type        = number
  default     = 3600 # 1 hour
}

# ----------------------------------------------------------------------------
# Locals -- PROV action wiring reuses the shared local.page_action /
# local.ticket_action (declared in observability_alarms.tf). No action unless
# arm_paging=true AND the PROV key is opted into paging_armed_alarms.
# ----------------------------------------------------------------------------

locals {
  prov1_actions = contains(var.paging_armed_alarms, "PROV-1") ? local.page_action : local.ticket_action
  prov2_actions = contains(var.paging_armed_alarms, "PROV-2") ? local.page_action : local.ticket_action
  prov3_actions = contains(var.paging_armed_alarms, "PROV-3") ? local.page_action : local.ticket_action
  prov4_actions = contains(var.paging_armed_alarms, "PROV-4") ? local.page_action : local.ticket_action
  prov5_actions = contains(var.paging_armed_alarms, "PROV-5") ? local.page_action : local.ticket_action
  prov6_actions = contains(var.paging_armed_alarms, "PROV-6") ? local.page_action : local.ticket_action
}

# ----------------------------------------------------------------------------
# PROV-1 -- UnprovableCount > 0  (fires ON unprovability; SILENT on all-provable).
#
# The alarm-feeding evaluation FIRES when any artifact reads STALE, CORRUPT, or
# MISSING in a sweep (unprovable_count >= 1), and stays SILENT on an all-provable
# run (unprovable_count == 0) -- the two-sided teeth, proven in test_observe.py.
# treat_missing_data=notBreaching: evaluator ABSENCE is PROV-2's job, not this
# alarm's (separation keeps "data is unprovable" distinct from "evaluator is dead").
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "prov1_unprovable" {
  alarm_name          = "asana-PROV-1-unprovable"
  alarm_description   = "substrate-v2 provability sweep found >= 1 UNPROVABLE artifact (stale/corrupt/missing) via the SAME is_provable the serve gate uses ([H19]). RB-SUBSTRATE-PROVABILITY. Cannot read green while a served number would be refused."
  namespace           = var.substrate_provability_namespace
  metric_name         = "UnprovableCount"
  dimensions          = { environment = var.environment }
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = var.evaluation_schedule_seconds
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching" # evaluator absence -> PROV-2, not here

  alarm_actions = local.prov1_actions
  ok_actions    = local.prov1_actions
}

# ----------------------------------------------------------------------------
# PROV-2 -- evaluator heartbeat absence  (the DEAD-MAN DONE RIGHT).
#
# EvaluatorHeartbeat = 1 is emitted on EVERY scheduled run (even an empty sweep),
# so it is a metric that EXISTS while healthy. A window with < 1 heartbeat (Sum),
# or NO datapoint at all (treat_missing_data=breaching), means the scheduled
# evaluator itself stopped -- absence is a breach. This is exactly what the
# orphaned `…-DMS-24h` could NOT do: it watched a now-empty namespace, so its
# silence was ambiguous. Here silence is unambiguous.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "prov2_heartbeat_absence" {
  alarm_name          = "asana-PROV-2-heartbeat-absence"
  alarm_description   = "substrate-v2 ProvabilityEvaluator stopped heartbeating (< 1 EvaluatorHeartbeat in the dead-man window, or none at all). RB-SUBSTRATE-EVALUATOR-DOWN. Dead-man on a metric that EXISTS every healthy run -- the query-independent cure for the DMS-24h-on-a-dead-metric class."
  namespace           = var.substrate_provability_namespace
  metric_name         = "EvaluatorHeartbeat"
  dimensions          = { environment = var.environment }
  statistic           = "Sum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = var.heartbeat_deadman_period_seconds
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "breaching" # NO heartbeat datapoint == evaluator down == breach

  alarm_actions = local.prov2_actions
  ok_actions    = local.prov2_actions
}

# ----------------------------------------------------------------------------
# PROV-3 -- Completeness < 100  ([H20] completeness != heartbeat).
#
# A partial run that heartbeats but SKIPS a broken artifact (an indeterminate
# read/check) reads INCOMPLETE, not green. Completeness = 100 * evaluated /
# expected; a skip drops it below 100 while PROV-2 still sees the heartbeat --
# the two signals are independent BY DESIGN (a run can be alive yet not have
# covered everything). Minimum over the window catches any incomplete sweep.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "prov3_incomplete" {
  alarm_name          = "asana-PROV-3-incomplete"
  alarm_description   = "substrate-v2 provability sweep COMPLETENESS < 100% -- an expected artifact was skipped (indeterminate read/check), so the run heartbeated but did NOT cover everything ([H20]). RB-SUBSTRATE-INCOMPLETE. Completeness != heartbeat; a partial run is never green."
  namespace           = var.substrate_provability_namespace
  metric_name         = "Completeness"
  dimensions          = { environment = var.environment }
  statistic           = "Minimum"
  comparison_operator = "LessThanThreshold"
  threshold           = 100
  period              = var.evaluation_schedule_seconds
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching" # evaluator absence -> PROV-2, not here

  alarm_actions = local.prov3_actions
  ok_actions    = local.prov3_actions
}

# ----------------------------------------------------------------------------
# PROV-4 -- ExpectedSetMismatchCount > 0  (C7 two-sided expected-set).
#
# expected-set = registry-warm-targets UNION store-enumeration(dataframes-v2/).
# A member present in exactly ONE set FIRES: registered-but-absent (also -> a
# MISSING verdict -> PROV-1) AND stored-but-unregistered EVEN WHILE FRESH. The
# second half is the AV-6 cure -- an unregistered-but-served frame can no longer
# rot green, because counts alone (evaluated == expected, all provable) do NOT
# read clean while the registry and the store disagree.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "prov4_expected_set_mismatch" {
  alarm_name          = "asana-PROV-4-expected-set-mismatch"
  alarm_description   = "substrate-v2 registry/store expected-set DISAGREE (>= 1 one-sided member): a registered-but-absent OR a stored-but-unregistered artifact (C7 two-sided). RB-SUBSTRATE-SET-DRIFT. Closes AV-6: an unregistered-but-served frame cannot rot green."
  namespace           = var.substrate_provability_namespace
  metric_name         = "ExpectedSetMismatchCount"
  dimensions          = { environment = var.environment }
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = var.evaluation_schedule_seconds
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching" # evaluator absence -> PROV-2, not here

  alarm_actions = local.prov4_actions
  ok_actions    = local.prov4_actions
}

# ----------------------------------------------------------------------------
# PROV-5 -- ExpectedCount < 1  (expected-set FLOOR; the "watching nothing" cure).
#
# expected-set = registry UNION store. Production ALWAYS expects >= 1 artifact, so
# ExpectedCount < 1 means the evaluator is watching NOTHING: either a common-mode
# ExpectedSetSource misconfiguration (wrong prefix/env, an impl that swallows its
# own errors into empty sets) reads registry=∅ ∧ store=∅, OR the expected-set fetch
# raised and the evaluator emitted a LOUD failed run (ExpectedCount=0). Without this
# floor an empty union reads vacuously green on PROV-1/3/4 (counts of nothing are all
# zero/100). Minimum over the window catches an intermittent empty/failed sweep at
# schedule granularity (the F-2/F-3 cure).
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "prov5_expected_floor" {
  alarm_name          = "asana-PROV-5-expected-floor"
  alarm_description   = "substrate-v2 provability sweep expected-set FLOOR breached: ExpectedCount < 1 -- the evaluator is watching NOTHING (empty registry ∧ empty store, or an expected-set fetch failure that emitted a loud failed run). RB-SUBSTRATE-EMPTY-EXPECTED. Production always expects >= 1 artifact; an empty union is a misconfiguration, not vacuous green."
  namespace           = var.substrate_provability_namespace
  metric_name         = "ExpectedCount"
  dimensions          = { environment = var.environment }
  statistic           = "Minimum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = var.evaluation_schedule_seconds
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching" # evaluator absence -> PROV-2, not here

  alarm_actions = local.prov5_actions
  ok_actions    = local.prov5_actions
}

# ----------------------------------------------------------------------------
# PROV-6 -- FutureDatedProofCount > 0  (the "super-fresh-while-broken" anomaly).
#
# A proof stamped in the FUTURE (writer clock skew / bad-stamp bug) yields NEGATIVE
# age. The frozen is_provable returns PROVABLE for it (negative age <= sla), so the
# provability axis is FOOLED -- but S6 discloses the anomaly rather than smoothing it
# away: MaxStalenessAgeSeconds is clamped >= 0 (never a raw negative "fresh" gauge)
# and this DISTINCT count FIRES. Discharges the S2-GO ledger condition (negative-age
# disclosure is Seam-5/Seam-6 charter per the S2 adversary F8 ruling); the full S5
# serving-side refusal obligation rides the handoff, not this alarm.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "prov6_future_dated_proof" {
  alarm_name          = "asana-PROV-6-future-dated-proof"
  alarm_description   = "substrate-v2 provability sweep found >= 1 FUTURE-DATED proof (built_from_live_at in the future -> negative age). RB-SUBSTRATE-FUTURE-STAMP. is_provable reads PROVABLE (age <= sla) so provability is fooled; this discloses the writer clock-skew / bad-stamp anomaly that would otherwise read super-fresh. The staleness gauge is clamped >= 0; this count is the loud signal."
  namespace           = var.substrate_provability_namespace
  metric_name         = "FutureDatedProofCount"
  dimensions          = { environment = var.environment }
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = var.evaluation_schedule_seconds
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching" # evaluator absence -> PROV-2, not here

  alarm_actions = local.prov6_actions
  ok_actions    = local.prov6_actions
}

# ----------------------------------------------------------------------------
# STAGED (DO NOT AUTHOR ITS DELETION HERE) -- DMS-24h retirement note.
#
# The orphaned `autom8-asana-cache-warmer-DMS-24h` (watches LastSuccessTimestamp
# in the now-EMPTY namespace `Autom8y/AsanaCacheWarmer` -- a dead-man on a dead
# metric) is SUPERSEDED by PROV-2 (heartbeat-absence on a metric that EXISTS) +
# PROV-1/3/4. Its retirement is a PROD-BEHAVIOR MUTATION (it is wired to the
# paging SNS `autom8y-platform-alerts`), so it is NOT executed here.
#
#   EXECUTION = DP-4b, at S11, in the PARENT repo `autom8y` (cross-repo; this
#   repo has no apply pipeline). The surfaced revert command is L-7 in
#   observability_alarms.SURFACED.md:
#       aws cloudwatch delete-alarms --region us-east-1 \
#         --alarm-names autom8-asana-cache-warmer-DMS-24h
#   Precondition (confirm-first): PROV-1/2/3/4 APPLIED + PROV-2 observed healthy
#   (>= 1 heartbeat/window) so the dead-man cure is live BEFORE the orphan is cut.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Outputs -- expose the authored alarm names (for a downstream apply pipeline).
# ----------------------------------------------------------------------------

output "authored_provability_alarm_names" {
  description = "All substrate-v2 provability alarm names authored by this suite (un-deployed)."
  value = [
    aws_cloudwatch_metric_alarm.prov1_unprovable.alarm_name,
    aws_cloudwatch_metric_alarm.prov2_heartbeat_absence.alarm_name,
    aws_cloudwatch_metric_alarm.prov3_incomplete.alarm_name,
    aws_cloudwatch_metric_alarm.prov4_expected_set_mismatch.alarm_name,
    aws_cloudwatch_metric_alarm.prov5_expected_floor.alarm_name,
    aws_cloudwatch_metric_alarm.prov6_future_dated_proof.alarm_name,
  ]
}

output "provability_paging_armed" {
  description = "Whether the PAGE tier is armed for the substrate-v2 provability suite."
  value       = var.arm_paging ? tolist([for k in var.paging_armed_alarms : k if startswith(k, "PROV-")]) : []
}
