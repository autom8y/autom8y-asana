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
  description = <<-EOT
    SNS topic ARN for the TICKET tier (non-paging). Optional.

    BINDING-BLIND WARNING (the defect this default caused): leaving this "" makes
    `local.ticket_action` resolve to [] for EVERY alarm in this module that is not
    page-armed -- the alarm evaluates, transitions to ALARM, and notifies NOBODY.
    That is not a safe default; it is a silent one. Measured live 2026-08-11
    (account 696318035277 / us-east-1): 7 of 20 `asana-*` alarms carried zero
    actions -- all 7 authored by THIS module -- while all 13 authored elsewhere
    were bound to `autom8y-platform-alerts`. Two of the seven
    (asana-AL5-offer-frame-stale-1143843662099250, asana-PROV-2-heartbeat-absence)
    were sitting in ALARM, unobserved.

    Set this (see terraform.tfvars.example) to bind the ticket tier. `terraform
    output alarm_binding_report` names the resolved binding for every alarm.
  EOT
  type        = string
  default     = ""
}

variable "create_ticket_topic" {
  description = <<-EOT
    Create an asana-owned SNS topic for the TICKET tier instead of pointing
    `ticket_sns_topic_arn` at an existing one. Default false.

    PREFER THE EXISTING TOPIC. A freshly created topic has ZERO subscriptions, so
    binding alarms to it RELOCATES the binding-blind defect rather than curing it
    (the alarm now publishes -- to no subscriber). `autom8y-platform-alerts`
    already carries a Slack-lambda + email subscription and is what every other
    live `asana-*` alarm uses. Only set this true if asana-owned ticket routing is
    wanted, and then subscribe an endpoint (an explicit operator decision -- this
    module deliberately authors NO aws_sns_topic_subscription).
  EOT
  type        = bool
  default     = false
}

variable "ticket_topic_name" {
  description = "Name for the optional asana-owned ticket topic (only when create_ticket_topic=true)."
  type        = string
  default     = "autom8y-asana-observability-tickets"
}

variable "require_alarm_binding" {
  description = <<-EOT
    Forcing function against the binding-blind class: when true, `terraform plan`
    FAILS if AL-5 would be created with an empty action list (detect-and-tell-nobody).
    Default false so this module's existing apply doors (incl. the DP-4a PROV door)
    are not broken by adding the guard; the operator apply card sets it true.
  EOT
  type        = bool
  default     = false
}

# ----------------------------------------------------------------------------
# Optional asana-owned TICKET topic. Guarded: does not exist unless enabled.
# No subscription is authored here -- endpoint choice is an operator decision.
# ----------------------------------------------------------------------------

resource "aws_sns_topic" "observability_tickets" {
  count = var.create_ticket_topic ? 1 : 0

  name         = var.ticket_topic_name
  display_name = "autom8y-asana observability tickets"

  tags = {
    service   = "autom8y-asana"
    tier      = "ticket"
    managedby = "terraform"
    module    = "terraform/services/asana"
  }
}

# ----------------------------------------------------------------------------
# Locals -- action wiring resolves to [] (no action) unless explicitly armed.
# ----------------------------------------------------------------------------

locals {
  # TICKET topic resolution: an explicit ARN wins; else the optional asana-owned
  # topic if created; else "" (== the binding-blind state, now reported, not silent).
  # Splat+join, not [0]: with count=0 an index would be an "Invalid index" footgun;
  # join over the splat yields "" for the empty case and the ARN for the one case.
  created_ticket_topic_arn = join("", aws_sns_topic.observability_tickets[*].arn)

  # The `var.create_ticket_topic ? ... : ""` arm is load-bearing, not redundant:
  # it keeps the UNBOUND case resolvable from VARIABLES ALONE, so the binding
  # report below reads a definite "UNBOUND" instead of "(known after apply)".
  # Deriving it from the resource attribute made the blind state render as
  # unknown -- i.e. the visibility cure went dark in exactly the case it exists
  # to expose. Only the genuinely-creating case defers to apply-time.
  ticket_topic_arn = (
    var.ticket_sns_topic_arn != "" ? var.ticket_sns_topic_arn :
    var.create_ticket_topic ? local.created_ticket_topic_arn : ""
  )

  # Per-alarm page action: empty unless master switch on AND alarm opted-in.
  page_action   = var.arm_paging && var.page_sns_topic_arn != "" ? [var.page_sns_topic_arn] : []
  ticket_action = local.ticket_topic_arn != "" ? [local.ticket_topic_arn] : []

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
    AL-5 staleness threshold (seconds). 7200 = "served frame BUILT more than 120 min
    ago". The 7200 number was ORIGINALLY chosen to mirror the ASR readiness gate's
    120-min abort threshold, on the (then-true) assumption that the two alarms read
    the same quantity.

    *** THAT ALIGNMENT IS DEAD (2026-08-11 content-axis cure). ***
    This threshold is NO LONGER an ASR-abort predictor and 7200 no longer has an
    ASR-derived justification -- it is currently an UNANCHORED number inherited from
    a superseded axis. The ASR gate now aborts on CONTENT-WATERMARK age (how old the
    DATA is); this variable thresholds SERVED-FRAME age (how long ago the frame was
    BUILT). Live falsification, same GID, same instant: at 2026-08-11T20:01:22Z the
    ASR gate read offers staleness_seconds=83123.29 and ABORTED, while this alarm's
    input read 6581.3s -- 12.6x apart, below threshold, alarm OK. See the RE-POINT
    block above the al5_offer_frame_stale resource for the pending re-baseline and
    the recommended successor semantics (operator interview item C2).

    HISTORY (superseded reasoning, left standing per amend-in-place convention).
    F1a pacing re-scope (2026-08-05): raised 3600 -> 7200. The prior 3600 (60 min)
    was DEGENERATE against the pre-cure OfferFrameAgeSeconds sawtooth (peaks 674-1231
    min, i.e. 10-20x the threshold) -- trivially always-breaching, non-actionable --
    and it also fired on 60-120 min peaks that do NOT cause an ASR abort. The pacing
    cure collapses the peak below 120 min, so 7200 WAS THEN the actionable "an ASR
    abort would have happened" line -- true on 2026-08-05, false since the
    2026-08-11 cure moved the gate to the content axis. Still LOOSER than the code
    FRESH TTL (offer=180s,
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

# ----------------------------------------------------------------------------
# AL-5 RE-POINT BLOCK (authored 2026-08-12, W-2 / pythia P-7 + P-8).
# NOT APPLIED. Description text only; no threshold, window, or action changed.
#
# (1) WHAT WAS FALSE. The prior description asserted AL-5 "fires iff an ASR tick
#     landing in the window would abort". That was true when authored and is
#     FALSE now. The 2026-08-11 content-axis cure re-pointed the ASR readiness
#     gate at CONTENT-WATERMARK age; AL-5 still reads SERVED-FRAME BUILD age.
#     Two different quantities, decoupled in BOTH directions. Receipts:
#       - GREEN-while-aborting: 2026-08-11T20:01:22Z the gate read offers
#         staleness_seconds=83123.29 ("1385 min stale") and ABORTED; AL-5's own
#         input in that bucket read Max=6581.3s (< 7200) and AL-5 was OK.
#       - Same shape 2026-08-12T08:01:02Z: gate 45069.21s ABORT; AL-5 input
#         6585.0s in the preceding bucket; AL-5 cleared to OK 48s after the abort.
#     Ratio between the two axes ran 6.8x-12.6x over the sampled aborts.
#     CODE RECEIPT (src/autom8_asana/cache/integration/dataframe_cache.py):
#       :136  age = datetime.now(UTC) - self.created_at   <- BUILD axis, feeds AL-5
#       :138  def is_fresh_by_watermark(current_watermark) <- CONTENT axis, separate
#     The two axes are distinct methods on the same object. The decoupling is
#     STRUCTURAL, not a tuning artifact -- no threshold change can close it.
#
# (2) NEW FINDING (not in the pythia consult): AL-5 IS FLAPPING. describe-alarm-
#     history shows TEN state transitions on 2026-08-12 ALONE (02:05:50Z ALARM,
#     03:05:50Z OK, 06:03:50Z ALARM, 07:05:50Z OK, 07:33:50Z ALARM, 08:01:50Z OK,
#     08:03:50Z ALARM, 08:05:50Z OK, 09:33:50Z ALARM, 09:35:50Z OK) -- five of
#     those alarms lasted <= 2 MINUTES. Every transition fires alarm_actions AND
#     ok_actions into autom8y-platform-alerts (live Slack + email subscribers),
#     so this is ~10 notifications/day of pure noise.
#     Cause: 2-of-8 M-of-N over 30-min buckets whose Max straddles 7200 on the
#     sawtooth. This is an active alert-fatigue generator independent of (1).
#
# (3) P-8 RE-BASELINE, PENDING (correction to the interview packet): FIX-N-C1
#     (asana PR #339) changes preload-hydrated entries' created_at from now() to
#     the s3_watermark, so OfferFrameAgeSeconds jumps from ~0-anchored to TRUE
#     SUBSTRATE AGE. As of 2026-08-12T09:40Z #339 is still OPEN and titled
#     [MERGE-HELD] -- it did NOT merge at 09:20Z as the packet assumed, so the
#     boundary is AHEAD, not behind. When it lands: the 7200 / 2-of-8 tuning was
#     calibrated on the PRE-C1 sawtooth (2026-08-05) and NO reading is comparable
#     across the boundary. Re-baseline from >=7 days of post-merge data before
#     reading any AL-5 trend. Do not hold #339 for this.
#
# (4) RECOMMENDATION ONLY -- NOT A DECISION. Operator interview item C2(ii),
#     "what SHOULD AL-5 predict now?". Recommended: keep AL-5 on the BUILD/SERVE
#     axis and stop pretending it is an ASR predictor. Concretely:
#       a. Re-scope AL-5 to its actual and still-valuable job: per-GID serve-path
#          starvation (the SCAR-015 cure). That job is real and nothing else
#          covers it.
#       b. Do NOT re-point AL-5 at the content axis. The ASR gate already owns
#          that axis and owns it better (it reads the manifest directly); a second
#          content-axis alarm re-imports the co-sourcing shape §1.4 forbids.
#       c. Re-derive the threshold from the SERVE contract, not from ASR. The
#          honest anchors are the code's own bands (FRESH TTL 180s, STALE onset
#          900s, FRESHNESS_CONTRACT_MAX_AGE 16200s), not 7200.
#       d. Fix the flap first (2): widen to Minimum-over-window or raise M, and
#          drop ok_actions. Flap-fixing is independent of the re-point and can
#          ship alone.
#       e. Sequence: fix flap -> land #339 -> re-baseline 7 days -> then set the
#          new threshold. Setting a number before the re-baseline is guesswork.
#       f. The ASR-abort predictor AL-5 was pretending to be does not exist and
#          is NOT re-creatable on this metric. If one is wanted, it belongs on the
#          ASR side keyed on the gate's own quantity.
# ----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "al5_offer_frame_stale" {
  for_each = var.substrate_freshness_gids

  alarm_name        = "asana-AL5-offer-frame-stale-${each.key}"
  alarm_description = "PER-GID SERVED-FRAME BUILD AGE for project_gid=${each.key}: the LKG frame being served was BUILT more than ${var.offer_frame_stale_threshold_seconds}s ago, on 3-of-4 hourly datapoints over a 4h window (missing data IGNORED, not counted healthy). AXIS: BUILD/SERVE (dataframe_cache_memory_lkg_serve extra.age_seconds = age of the frame), NOT content. THIS IS NOT AN ASR-ABORT PREDICTOR -- since the 2026-08-11 content-axis cure the ASR readiness gate aborts on CONTENT-WATERMARK age, a different quantity. Decoupled BOTH ways, proven live: 2026-08-11T20:01:22Z the gate read offers staleness 83123s and ABORTED while this alarm read 6581s and stayed OK. AL-5 can be GREEN while every ASR tick aborts, and RED while ticks would pass. Do not infer ASR readiness from this alarm. Valid use: per-GID serve-path starvation (SCAR-015 cure). Threshold 7200 is inherited from the dead ASR alignment and is pending re-baseline after FIX-N-C1 (#339). RB-SUBSTRATE-FRESHNESS. NON-PAGING until armed + apply-imported; confirm-first."
  namespace         = var.substrate_freshness_namespace
  metric_name       = "OfferFrameAgeSeconds"
  dimensions = {
    project_gid = each.key
  }
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.offer_frame_stale_threshold_seconds
  # FLAP CURE (2026-08-12, W-2 / P-7(b)). SUPERSEDES the F1a sampling numbers below;
  # the F1a INTENT -- eval span == one 4h ASR tick -- is PRESERVED EXACTLY (3600 x 4
  # == 1800 x 8 == 4h). Threshold, statistic, metric, dimensions and BOTH action lists
  # are UNTOUCHED by this change.
  #
  # THE DISEASE (measured, not inferred). describe-alarm-history for
  # asana-AL5-offer-frame-stale-1143843662099250 shows ELEVEN state transitions in the
  # 21h to 2026-08-12T09:35:50Z -- 12.6 per 24h -- five of them ALARM episodes lasting
  # <= 2 MINUTES. alarm_actions AND ok_actions both route to autom8y-platform-alerts
  # (live Slack + email), so every transition is a notification: ~12.6 pages/day of
  # pure noise. This is an alert-fatigue generator and it is INDEPENDENT of the
  # axis-decoupling defect cured in the description above.
  #
  # THE MECHANISM (verbatim receipts, two consecutive live evaluations 4 min apart):
  #   eval 2026-08-12T08:01:50Z -> "6894.3 (12/08/26 07:31:00), 6585.0 (12/08/26 03:31:00)"  -> OK
  #   eval 2026-08-12T08:03:50Z -> "7300.5 (12/08/26 06:03:00), 12448.4 (12/08/26 05:33:00)" -> ALARM
  #   eval 2026-08-12T08:05:50Z -> "6894.3 (12/08/26 07:35:00), 6585.0 (12/08/26 03:35:00)"  -> OK
  # The SAME two sample values (6894.3 / 6585.0) are reported at bucket-starts :31 and
  # then :35 -- i.e. the 1800s bucket ANCHOR DRIFTS between evaluations, and with a
  # Maximum statistic over a SPARSE series that re-bucketing alternately MERGES and
  # SPLITS a pair of near-threshold samples one period apart, flipping the breaching
  # count across M=2 every two minutes. The state is a function of bucket alignment,
  # not of what the service did.
  #
  # WHY THE 1800s BUCKET IS THE ROOT SAMPLING ERROR (measured over 2026-08-09T12:00Z
  # -> 2026-08-12T09:17Z, 66 serve-event minutes in 69.3h):
  #   median inter-serve-event gap = 56 min   (p90 132 min, max 240 min)
  #   bucket density: 1800s -> 38.1% populated | 3600s -> 70.0% | 7200s -> 91.4%
  # A 1800s bucket is SMALLER THAN THE MEDIAN INTER-EVENT GAP, so ~62% of the
  # evaluation window is synthetic filler. Under treat_missing_data=notBreaching that
  # filler also handed the ALARM->OK test 5 of the 7 non-breaching datapoints it needs
  # for free -- the live StateReason says so verbatim: "5 missing datapoints were
  # treated as [NonBreaching] (minimum 7 datapoints for ALARM -> OK transition)".
  # Recovery was therefore driven by absence of data, not by evidence of health.
  #
  # THE FOUR CHANGES, each inside the operator's authorized lever set
  # (M-of-N / evaluation-period stretch / missing-data treatment):
  #   period 1800 -> 3600           bucket >= median inter-event gap; density 38%->70%,
  #                                 halving the boundaries a lone sample can drift over.
  #   evaluation_periods 8 -> 4     holds the eval span at EXACTLY 4h (F1a intent kept).
  #   datapoints_to_alarm 2 -> 3    3 of the last 4 observed hours must breach; a single
  #                                 re-bucketed spike moves the count by 1 and can no
  #                                 longer carry the transition alone. ALARM->OK bar
  #                                 becomes N-M+1 = 2 REAL non-breaching observations.
  #   treat_missing_data
  #     "notBreaching" -> "missing" evaluate OBSERVATIONS, not filler. Removes the free
  #                                 non-breaching datapoints that made recovery
  #                                 automatic. NOT a regression of the darkness blind
  #                                 spot: notBreaching already forced a fully-dark GID
  #                                 to OK; "missing" merely holds the last honest state
  #                                 instead of asserting health. Darkness detection is
  #                                 still NOT this alarm's job (see header).
  #
  # MODELLED EFFECT (state machine replayed against the real 69h sample series; the
  # model is validated -- it reproduces the live 12.6 transitions/24h AND the
  # characteristic 2-minute :04->:06 / :34->:36 flap pairs):
  #   current  1800/8/2 notBreaching -> 12.5 transitions/24h, 14.0% alarm duty
  #   authored 3600/4/3 missing      ->  6.6 transitions/24h, 14.6% alarm duty
  # A 1.9x reduction in notifications with sensitivity held flat.
  #
  # HONEST LIMIT -- STATED, NOT HIDDEN. This DAMPS the flap; it does not ELIMINATE it.
  # A 100+ config sweep over period x evaluation_periods x datapoints_to_alarm x
  # missing-data found NO configuration inside the authorized lever set with a minimum
  # dwell above 2 minutes that still fires meaningfully: every config with a lower flap
  # rate than the above bought it by dropping alarm duty toward 0 (i.e. by not firing).
  # The residual 2-minute flap is inherent to Maximum-over-sparse-buckets under anchor
  # drift. Two levers WOULD cure it and are DELIBERATELY NOT AUTHORED here because they
  # sit outside the authorized lever set and change semantics rather than sampling:
  #   (i)  drop ok_actions -- halves notifications at a stroke (one line), at the cost
  #        of losing auto-resolve notices;
  #   (ii) move to a composite or anomaly-detection alarm.
  # Either is a one-word operator decision; neither is taken unilaterally.
  #
  # POST-C1 REGIME ASSUMPTION -- THE THING TO FALSIFY AT RE-BASELINE.
  # This is tuned for the signal that starts NOW, not the dead pre-C1 sawtooth.
  # rev-762 (task definition autom8y-asana-service:762, carrying FIX-N-C1 / PR #339,
  # merged 2026-08-12T10:24:13Z) reached rolloutState COMPLETED at 2026-08-12T11:04:18Z.
  # From that instant, per the merged diff, the ONE sanctioned call site
  # (api/preload/progressive.py) passes created_at=s3_watermark into put_async, so
  # preload-hydrated entries stop reporting BOOT-CLOCK uptime and start reporting the
  # substrate's own recency. ASSUMED consequences:
  #   1. the deploy-synchronised reset to ~0 DISAPPEARS (age no longer restarts with
  #      the worker);
  #   2. the baseline RISES -- possibly far above 7200. The ASR gate reading the
  #      substrate axis on the same days saw 45069s and 83123s;
  #   3. the series stays a MIXTURE, because freshly-BUILT entries still stamp now()
  #      (the diff is explicitly default-preserving: created_at=None -> now()).
  # FALSIFIABLE PREDICTION: AL-5 alarm duty at threshold 7200 will RISE, not fall,
  # trending toward sustained ALARM after a worker restart against an aged parquet.
  # If duty instead collapses toward 0%, THIS ASSUMPTION IS WRONG and the tuning must
  # be re-opened.
  #
  # RE-BASELINE GATE (binding on the threshold, NOT on this change). 7200 is an ORPHAN
  # -- it was derived from the now-dead ASR alignment and has NO post-C1 justification.
  # It is deliberately LEFT ALONE here: setting a number before the re-baseline is
  # guesswork. Re-open at >= 48h of post-rollout data, i.e. from ~2026-08-14T11:04Z,
  # and confirm three things against the NEW regime: (i) realised transitions/24h,
  # (ii) alarm duty, (iii) the value distribution relative to 7200. Only then set the
  # threshold, and only from the SERVE contract (FRESH TTL 180s, STALE onset 900s,
  # FRESHNESS_CONTRACT_MAX_AGE 16200s) per item (4c) of the RE-POINT block above.
  #
  # SUPERSEDED (left standing per amend-in-place convention).
  # F1a PACING RE-SCOPE (2026-08-05, two-sided-teeth-proven): align the window to the
  # ASR 4h tick cadence and the threshold to the 120-min abort line so AL-5 predicts
  # ASR aborts instead of reading always-red against the pre-cure sawtooth. Period
  # 3600->1800, EvaluationPeriods 12->8 (== 4h), DatapointsToAlarm 2 (M-of-N: 2-of-8
  # over 4h) keeps the sparsity cure (a starved GID served a handful of times over the
  # window still trips) while bounding the eval span to one ASR tick. Supersedes the
  # 2026-07-20 EXECUTION-RECEIPT-al5-reconfig 3600/12/2 config (which cured the earlier
  # 300s/2-of-2 sparsity blindness but read degenerate against the 10-20x sawtooth).
  # [The 1800/8/2 sampling above is SUPERSEDED by the FLAP CURE. The "predicts ASR
  #  aborts" rationale is separately FALSE since 2026-08-11 -- see the description.]
  period              = 3600
  evaluation_periods  = 4
  datapoints_to_alarm = 3
  treat_missing_data  = "missing" # evaluate observations, not filler; see FLAP CURE above

  alarm_actions = local.al5_actions
  # ok_actions DROPPED (operator ruling 2026-08-12, stage-1 apply sitting): halves the
  # notification volume the residual 2-min flap can generate (see HONEST LIMIT above);
  # auto-resolve notices forfeited deliberately. Explicit [] so the drop reads as ruled,
  # not as an accidental omission.
  ok_actions = []

  depends_on = [aws_cloudwatch_log_metric_filter.al5_offer_frame_age]

  # BINDING-BLIND GUARD (3rd-occurrence cure). AL-5 is the one alarm in this
  # module with two-sided teeth proven live, so it is the one that most earns a
  # route. With require_alarm_binding=true this refuses to plan a mute AL-5.
  lifecycle {
    precondition {
      condition     = !var.require_alarm_binding || length(local.al5_actions) > 0
      error_message = "AL-5 would be created with an EMPTY action list: it would detect offer-frame staleness and notify nobody. Set ticket_sns_topic_arn (recommended: the existing arn:aws:sns:us-east-1:696318035277:autom8y-platform-alerts, which has live Slack+email subscribers) or create_ticket_topic=true plus a subscription. See terraform.tfvars.example."
    }
  }
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

output "ticket_topic_arn" {
  description = "Resolved TICKET-tier topic ARN ('' when the ticket tier is unbound)."
  value       = local.ticket_topic_arn
}

# ----------------------------------------------------------------------------
# BINDING REPORT -- the structural cure for the binding-blind class.
#
# Every alarm in this module resolves its notification target through a local.
# Until now that resolution was INVISIBLE: an empty `ticket_sns_topic_arn` sent
# every unarmed alarm to [] and nothing in plan/apply output said so. Three
# occurrences of "alarm detects, tells no one" have now been observed on this
# fleet. This output makes the binding an ALWAYS-VISIBLE, per-alarm fact, so the
# blind state has to be read past rather than merely not-noticed:
#
#   terraform output alarm_binding_report
#
# It is deliberately not gated behind a flag -- unlike require_alarm_binding
# (opt-in teeth), this costs nothing and is the part that always fires.
# ----------------------------------------------------------------------------

output "alarm_binding_report" {
  description = "Per-alarm resolved notification binding. Any UNBOUND entry is an alarm that will detect and notify nobody."
  value = {
    for k, actions in {
      "AL-1"   = local.al1_actions
      "AL-2"   = local.al2_actions
      "AL-3"   = local.al3_actions
      "AL-4"   = local.al4_actions
      "AL-5"   = local.al5_actions
      "AL-6"   = local.al6_actions
      "PROV-1" = local.prov1_actions
      "PROV-2" = local.prov2_actions
      "PROV-3" = local.prov3_actions
      "PROV-4" = local.prov4_actions
      "PROV-5" = local.prov5_actions
      "PROV-6" = local.prov6_actions
    } : k => length(actions) > 0 ? "BOUND -> ${join(", ", actions)}" : "UNBOUND -- detects and notifies NOBODY"
  }
}
