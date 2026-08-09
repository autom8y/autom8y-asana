# ============================================================================
# autom8y-asana observability alarm suite (AL-1 .. AL-6)
# ============================================================================
#
# Source of truth: .ledge/reviews/sre-observability-design.md §B-2 (N1) +
#                  .ledge/reviews/sre-dark-subsystem-postmortem.md §4 (AI-7).
#
# STATUS: AUTHORED / UN-DEPLOYED / UN-ARMED.
#   - This module is NOT wired into any apply pipeline by this change.
#   - Every alarm is authored WITHOUT an SNS/pager action by default.
#   - Paging is a SURFACED operator lever, gated behind `arm_paging` (default
#     false) AND a per-alarm membership in `paging_armed_alarms` (default []).
#   - Arming the PAGE tier is a distinct, confirm-first operator action
#     (G-RUNG: an authored alarm is `authored`, not `alerting`; it only
#     reaches `alerting` once an operator arms it). See the exact surfaced
#     commands in observability_alarms.SURFACED.md.
#
# Rung discipline: a metric proven in a test fixture is `emitting`, NOT
# `proven` in prod. These alarms watch metrics; AL-1 watches StatusPushSkipped
# (emitting in fixtures only until the instrumented Lambda is deployed). The
# alarm IaC is therefore `authored` at HEAD; do not round up.
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# ----------------------------------------------------------------------------
# Variables -- safe defaults: NOTHING arms a pager on apply.
# ----------------------------------------------------------------------------

variable "environment" {
  description = "Deployment environment dimension value (e.g. production, staging)."
  type        = string
  default     = "production"
}

variable "bridge_fleet_namespace" {
  description = "Shared bridge fleet CloudWatch namespace."
  type        = string
  default     = "Autom8y/AsanaBridgeFleet"
}

variable "insights_dms_namespace" {
  description = "insights-export dead-man-switch namespace."
  type        = string
  default     = "Autom8y/AsanaInsights"
}

variable "recon_function_name" {
  description = "Account-status recon Lambda FunctionName dimension."
  type        = string
  default     = "autom8y-account-status-recon"
}

variable "recon_rule_enabled" {
  description = <<-EOT
    Whether the recon EventBridge schedule is ENABLED. AL-2 (recon-invocation-gap)
    would page on an intended-off cron if armed while the rule is DISABLED
    (postmortem Symptom 1 = EXPECTED, cron OFF). AL-2 paging is therefore gated
    on this being true AND the operator arming it. Default false mirrors the
    live State=DISABLED observed 2026-06-24 -- SURFACE-only until re-enabled.
  EOT
  type        = bool
  default     = false
}

variable "arm_paging" {
  description = <<-EOT
    MASTER paging kill-switch. Default false: no alarm has an SNS/pager action.
    Set true AND list the alarm keys in `paging_armed_alarms` to arm. This is a
    confirm-first operator lever; arming is NOT performed by this change.
  EOT
  type        = bool
  default     = false
}

variable "paging_armed_alarms" {
  description = <<-EOT
    Per-alarm opt-in for paging. Subset of {AL-1 .. AL-6}. Only alarms
    listed here (and only when arm_paging=true) receive the page SNS action.
    Default [] -- TICKET-only / no action.
  EOT
  type        = set(string)
  default     = []
}

variable "page_sns_topic_arn" {
  description = "SNS topic ARN for the PAGE tier. Required only when arming."
  type        = string
  default     = ""
}

variable "ticket_sns_topic_arn" {
  description = "SNS topic ARN for the TICKET tier (non-paging). Optional."
  type        = string
  default     = ""
}

# ----------------------------------------------------------------------------
# Locals -- action wiring resolves to [] (no action) unless explicitly armed.
# ----------------------------------------------------------------------------

locals {
  # Per-alarm page action: empty unless master switch on AND alarm opted-in.
  page_action   = var.arm_paging && var.page_sns_topic_arn != "" ? [var.page_sns_topic_arn] : []
  ticket_action = var.ticket_sns_topic_arn != "" ? [var.ticket_sns_topic_arn] : []

  al1_actions = contains(var.paging_armed_alarms, "AL-1") ? local.page_action : local.ticket_action
  al2_actions = (contains(var.paging_armed_alarms, "AL-2") && var.recon_rule_enabled) ? local.page_action : local.ticket_action
  al3_actions = contains(var.paging_armed_alarms, "AL-3") ? local.page_action : local.ticket_action
  al4_actions = contains(var.paging_armed_alarms, "AL-4") ? local.page_action : local.ticket_action
  al5_actions = contains(var.paging_armed_alarms, "AL-5") ? local.page_action : local.ticket_action
  al6_actions = contains(var.paging_armed_alarms, "AL-6") ? local.page_action : local.ticket_action
}

# ----------------------------------------------------------------------------
# AL-1 -- StatusPushSkipped > 0 (per skip_reason).
# TICKET-first (baseline unknown; could be benign three_way_denominator_null).
# Misconfig reasons (url_absent / invalid_key) graduate to PAGE post-baseline
# by adding "AL-1" to paging_armed_alarms. Authored here per-reason.
# ----------------------------------------------------------------------------

variable "status_push_skip_reasons" {
  description = "Closed skip_reason enum emitted by StatusPushSkipped."
  type        = set(string)
  default = [
    "feature_disabled",
    "url_absent",
    "invalid_key",
    "three_way_denominator_null",
  ]
}

resource "aws_cloudwatch_metric_alarm" "al1_status_push_skipped" {
  for_each = var.status_push_skip_reasons

  alarm_name        = "asana-AL1-StatusPushSkipped-${each.key}"
  alarm_description = "StatusPush seam skipped with reason=${each.key}. RB-STATUSPUSH-SKIP. TICKET-first; url_absent/invalid_key graduate to PAGE post-baseline."
  namespace         = var.bridge_fleet_namespace
  metric_name       = "StatusPushSkipped"
  dimensions = {
    environment = var.environment
    skip_reason = each.key
  }
  statistic           = "Sum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = 3600
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = local.al1_actions
  ok_actions    = local.al1_actions
}

# ----------------------------------------------------------------------------
# AL-2 -- recon-invocation-gap (< 1 invocation / 8h).
# Rule fires q4h when ENABLED -> 2 expected/8h; alarm at <1. PAGE only after
# the rule is re-ENABLED (recon_rule_enabled=true) AND armed -- else it would
# page on the intended-off state (postmortem Symptom 1 = EXPECTED).
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "al2_recon_invocation_gap" {
  alarm_name        = "asana-AL2-recon-invocation-gap"
  alarm_description = "Account-status recon Lambda invoked < 1x in 8h. RB-RECON-GAP. PAGE only after the EventBridge rule is re-ENABLED (recon_rule_enabled). While DISABLED this is a TICKET, not a page (intended-off, not an outage)."
  namespace         = "AWS/Lambda"
  metric_name       = "Invocations"
  dimensions = {
    FunctionName = var.recon_function_name
  }
  statistic           = "Sum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = 28800 # 8h
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "breaching"

  alarm_actions = local.al2_actions
  ok_actions    = local.al2_actions
}

# ----------------------------------------------------------------------------
# AL-3 -- insights-export LastSuccessTimestamp stale (> 26h).
# Daily cadence + 2h grace. Symptom-of-record for the insights darkness.
# LastSuccessTimestamp is published as epoch seconds; staleness = now - latest.
# Modeled as: the freshness metric's Maximum (latest timestamp) age. Because a
# raw "age(now - latest)" is not a native CloudWatch comparison, this alarm
# watches for the ABSENCE of a fresh datapoint within the 26h window via
# treat_missing_data=breaching on a 26h period -- if no LastSuccessTimestamp
# datapoint lands in 26h, the metric is missing -> breaching.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "al3_insights_lst_stale" {
  alarm_name          = "asana-AL3-insights-LastSuccessTimestamp-stale"
  alarm_description   = "insights-export LastSuccessTimestamp not advanced within 26h (daily cadence + 2h grace). RB-INSIGHTS-STALE. The freshness dead-man is user-facing-data staleness."
  namespace           = var.insights_dms_namespace
  metric_name         = "LastSuccessTimestamp"
  statistic           = "Maximum"
  comparison_operator = "LessThanThreshold"
  # Threshold 1: any published epoch-second timestamp is >> 1; the load-bearing
  # signal is treat_missing_data=breaching over the 26h window -- a fresh emit
  # keeps the datapoint present (OK); a stale day produces a missing datapoint
  # (breaching). Threshold guards against a degenerate 0 emit.
  threshold           = 1
  period              = 93600 # 26h
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "breaching"

  alarm_actions = local.al3_actions
  ok_actions    = local.al3_actions
}

# ----------------------------------------------------------------------------
# AL-4 -- PROD BridgeFleetHealth < 1 (0.0 = ran-but-failed).
# NOTE (proven gap, N1 §B-2): the {environment=production} dimension does NOT
# exist today -- only {environment=staging, workflow_id=insights-export}. This
# alarm is authored against the intended prod dimension; it will stay in
# INSUFFICIENT_DATA until AI-5 (add `environment` to the BridgeFleetHealth emit)
# is deployed. Authored, not alerting.
# ----------------------------------------------------------------------------

variable "bridge_workflow_ids" {
  description = "Bridge workflow_id dimension values to alarm on for prod fleet health."
  type        = set(string)
  default     = ["insights-export"]
}

resource "aws_cloudwatch_metric_alarm" "al4_prod_bridge_fleet_health" {
  for_each = var.bridge_workflow_ids

  alarm_name        = "asana-AL4-prod-BridgeFleetHealth-${each.key}"
  alarm_description = "Prod BridgeFleetHealth < 1 (0.0 = ran-but-failed) for workflow_id=${each.key}. RB-BRIDGEFLEET. Requires AI-5 (environment dimension) deployed to emit a production series."
  namespace         = var.bridge_fleet_namespace
  metric_name       = "BridgeFleetHealth"
  dimensions = {
    environment = var.environment
    workflow_id = each.key
  }
  statistic           = "Minimum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = 3600
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "missing" # absence is its own AI-5 signal, not a breach

  alarm_actions = local.al4_actions
  ok_actions    = local.al4_actions
}

# ----------------------------------------------------------------------------
# AL-5 -- PER-GID offer frame staleness (> stale threshold).
#
# WHY PER-GID (the SCAR-015 cure): the entity-level dead-man watches
# `offer:warm_complete:age_seconds{entity_type="offer"}`, which read 8.4-11.3ks
# ("healthy") on 2026-07-13 while the ASR project frame 1143843662099250 sat
# 74-87ks (~24h) stale on the SAME instant. Per-GID starvation is INVISIBLE to
# entity-level absence. This alarm keys on the served-frame age emitted per GID
# by the `dataframe_cache_memory_lkg_serve` serve event
# (src/autom8_asana/cache/integration/dataframe_cache.py -> extra.project_gid,
# extra.age_seconds), so a single starved GID trips even when the class is green.
#
# CARDINALITY (the design constraint that forced the class metric to be
# entity-level): a raw project_gid dimension is unbounded. This module bounds it
# by REGISTERING the GIDs that carry a freshness contract (var
# substrate_freshness_gids). One metric filter per registered GID -> the metric
# only ever emits the registered dimension values. Add a GID = add it to the set.
#
# EMISSION NOTE: the age series is emitted only when the frame is SERVED (queried).
# A registered-but-unqueried GID produces no datapoint; treat_missing_data is
# `notBreaching` here (missing != stale) -- a starved-AND-unqueried GID is a known
# residual blind spot, addressed by pairing this with a warm-liveness signal
# (see AL-6 candidate in the ownership ADR). Do not round up: this AL-5 catches
# starvation on the serve path, not silent non-service.
#
# LIVE-CANARY RECONCILIATION: the metric filter + a NON-PAGING AL-5 alarm were
# realized live via the AWS API on 2026-07-13 (in-lane non-paging observability)
# to PROVE the two-sided teeth (RED age=7200s -> ALARM; GREEN age=300s -> OK;
# real-log backtest 07-11..07-13 breaches vs entity-metric green). Names below
# match the live canary so a future `terraform import` adopts it rather than
# colliding. Until the apply pipeline imports, the live canary is the detecting
# surface and this TF is its authored codification (rung: detecting-via-canary,
# NOT protecting-prod -- paging is arm_paging-gated, confirm-first).
# ----------------------------------------------------------------------------

variable "substrate_freshness_gids" {
  description = <<-EOT
    Registered project GIDs that carry a per-GID freshness contract. Bounded set
    (cardinality guard) -- one metric filter + one AL-5 alarm per entry. Default
    is the ASR offer frame, the founding ticket of the substrate-freshness class.
  EOT
  type        = set(string)
  default     = ["1143843662099250"]
}

variable "offer_frame_stale_threshold_seconds" {
  description = <<-EOT
    AL-5 staleness threshold (seconds). 7200 = "served frame older than 120 min" ==
    the ASR readiness gate's abort threshold (ASR runs 4h ticks and aborts when the
    offer frame it reads is > 120 min old). Aligning AL-5 to the ASR abort threshold
    makes it a FAITHFUL ASR-abort predictor: it fires iff the frame is stale enough
    that an ASR tick landing in the window would abort.

    F1a pacing re-scope (2026-08-05): raised 3600 -> 7200. The prior 3600 (60 min)
    was DEGENERATE against the pre-cure OfferFrameAgeSeconds sawtooth (peaks 674-1231
    min, i.e. 10-20x the threshold) -- trivially always-breaching, non-actionable --
    and it also fired on 60-120 min peaks that do NOT cause an ASR abort. The pacing
    cure collapses the peak below 120 min, so 7200 is the actionable "an ASR abort
    would have happened" line. Still LOOSER than the code FRESH TTL (offer=180s,
    default=300s) / STALE onset (>900s) and within the LKG-servable band (offer
    FRESHNESS_CONTRACT_MAX_AGE=16200s); a separate tighter freshness alarm (toward the
    TTL) can be added later without conflating it with the ASR-abort gate.
  EOT
  type        = number
  default     = 7200
}

variable "substrate_freshness_namespace" {
  description = "CloudWatch namespace for the per-GID substrate-freshness metric."
  type        = string
  default     = "Autom8y/AsanaSubstrateFreshness"
}

variable "intake_office_phone_namespace" {
  description = "CloudWatch namespace for the intake Office Phone CF stamp alarm (AL-6)."
  type        = string
  default     = "Autom8y/AsanaIntakeCF"
}

variable "asana_service_log_group" {
  description = "ECS asana-service log group that emits dataframe_cache_memory_lkg_serve."
  type        = string
  default     = "/ecs/autom8y-asana-service"
}

# One metric filter per registered GID -> emits OfferFrameAgeSeconds{project_gid}
# from the serve event. Pattern restricts to the GID (bounded dimension).
resource "aws_cloudwatch_log_metric_filter" "al5_offer_frame_age" {
  for_each = var.substrate_freshness_gids

  name           = "asana-AL5-offer-frame-age-${each.key}"
  log_group_name = var.asana_service_log_group
  pattern        = "{ ($.event = \"dataframe_cache_memory_lkg_serve\") && ($.extra.project_gid = \"${each.key}\") }"

  metric_transformation {
    name      = "OfferFrameAgeSeconds"
    namespace = var.substrate_freshness_namespace
    value     = "$.extra.age_seconds"
    unit      = "Seconds"
    dimensions = {
      project_gid = "$.extra.project_gid"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "al5_offer_frame_stale" {
  for_each = var.substrate_freshness_gids

  alarm_name        = "asana-AL5-offer-frame-stale-${each.key}"
  alarm_description = "Per-GID offer frame staleness: served LKG frame for project_gid=${each.key} older than ${var.offer_frame_stale_threshold_seconds}s (== ASR 120-min abort threshold), 2-of-8 datapoints over a 4h ASR-tick window (M-of-N sparsity cure). Fires iff an ASR tick landing in the window would abort. RB-SUBSTRATE-FRESHNESS. Cures SCAR-015 entity-level blindness (per-GID axis). NON-PAGING until AL-5 armed + apply-imported; confirm-first."
  namespace         = var.substrate_freshness_namespace
  metric_name       = "OfferFrameAgeSeconds"
  dimensions = {
    project_gid = each.key
  }
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.offer_frame_stale_threshold_seconds
  # F1a PACING RE-SCOPE (2026-08-05, two-sided-teeth-proven): align the window to the
  # ASR 4h tick cadence and the threshold to the 120-min abort line so AL-5 predicts
  # ASR aborts instead of reading always-red against the pre-cure sawtooth. Period
  # 3600->1800, EvaluationPeriods 12->8 (== 4h), DatapointsToAlarm 2 (M-of-N: 2-of-8
  # over 4h) keeps the sparsity cure (a starved GID served a handful of times over the
  # window still trips) while bounding the eval span to one ASR tick. Supersedes the
  # 2026-07-20 EXECUTION-RECEIPT-al5-reconfig 3600/12/2 config (which cured the earlier
  # 300s/2-of-2 sparsity blindness but read degenerate against the 10-20x sawtooth).
  period              = 1800
  evaluation_periods  = 8
  datapoints_to_alarm = 2
  treat_missing_data  = "notBreaching" # missing serve != stale; residual blind spot per header

  alarm_actions = local.al5_actions
  ok_actions    = local.al5_actions

  depends_on = [aws_cloudwatch_log_metric_filter.al5_offer_frame_age]
}

# ----------------------------------------------------------------------------
# AL-6 -- intake Office Phone CF stamp unresolved (never-silent birth guard).
# A net-new business created via /v1/intake/business whose cf:Office Phone is
# never stamped is UNRESOLVABLE -> the calendly path mints a duplicate. Two
# silent-failure modes are made observable via a single metric:
#   - office_phone_cf_not_found   : the field gid could not be resolved (no write)
#   - office_phone_cf_stamp_failed: the update_async write raised (then re-raised)
# INTAKE-CF-1 / DEF-QA-1. TICKET-first; authored/un-armed like AL-1..AL-5.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_log_metric_filter" "al6_office_phone_stamp_unresolved" {
  name           = "asana-AL6-office-phone-stamp-unresolved"
  log_group_name = var.asana_service_log_group
  pattern        = "{ ($.event = \"office_phone_cf_not_found\") || ($.event = \"office_phone_cf_stamp_failed\") }"

  metric_transformation {
    name          = "OfficePhoneStampUnresolved"
    namespace     = var.intake_office_phone_namespace
    value         = "1"
    default_value = 0
  }
}

resource "aws_cloudwatch_metric_alarm" "al6_office_phone_stamp_unresolved" {
  alarm_name          = "asana-AL6-office-phone-stamp-unresolved"
  alarm_description   = "Intake Office Phone CF stamp unresolved (office_phone_cf_not_found | office_phone_cf_stamp_failed) > 0 in 1h: a net-new business was created without its resolver index key -> unresolvable -> calendly duplicate. RB-INTAKE-CF-1. TICKET-first; authored/un-armed (confirm-first). NON-PAGING until AL-6 armed."
  namespace           = var.intake_office_phone_namespace
  metric_name         = "OfficePhoneStampUnresolved"
  statistic           = "Sum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = 3600
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching" # no births != stamp-failure; blind until first emit

  alarm_actions = local.al6_actions
  ok_actions    = local.al6_actions

  depends_on = [aws_cloudwatch_log_metric_filter.al6_office_phone_stamp_unresolved]
}

# ----------------------------------------------------------------------------
# Outputs -- expose the authored alarm names (for a downstream apply pipeline).
# ----------------------------------------------------------------------------

output "authored_alarm_names" {
  description = "All alarm names authored by this suite (un-deployed)."
  value = concat(
    [for a in aws_cloudwatch_metric_alarm.al1_status_push_skipped : a.alarm_name],
    [aws_cloudwatch_metric_alarm.al2_recon_invocation_gap.alarm_name],
    [aws_cloudwatch_metric_alarm.al3_insights_lst_stale.alarm_name],
    [for a in aws_cloudwatch_metric_alarm.al4_prod_bridge_fleet_health : a.alarm_name],
    [for a in aws_cloudwatch_metric_alarm.al5_offer_frame_stale : a.alarm_name],
    [aws_cloudwatch_metric_alarm.al6_office_phone_stamp_unresolved.alarm_name],
  )
}

output "paging_armed" {
  description = "Whether the PAGE tier is armed (operator lever)."
  value       = var.arm_paging ? tolist(var.paging_armed_alarms) : []
}
