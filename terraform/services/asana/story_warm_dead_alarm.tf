# ============================================================================
# StoryWarm dead-man alarm — SEV-1 paging leg (nightly-smoke-resurrection CURE 2)
# ============================================================================
#
# WHY: detection existed, paging didn't. The story-warm lane emits a full
#   receipt surface (per-entity receipts + aggregate StoryWarm* metrics,
#   CC-5 #369) — and at authoring time NOT ONE alarm watched ANY StoryWarm
#   metric (verified live 2026-08-14: describe-alarms filtered on
#   MetricName startswith StoryWarm -> 0). A lane whose receipts nobody
#   watches is the binding-blind shape observability_alarms.tf:104-116
#   documents.
#
# WHAT PAGES (deliberately NOT a failure-count alarm): StoryWarmFailure is
#   ROUTINELY nonzero (7d baseline 2026-08-07..14: 89 of 152 hours nonzero,
#   p50 of nonzero hours = 19, max 100/h) — a failure>0 alarm would sit in
#   ALARM ~60% of the time: the AL-5 flap class reborn. The SEV-1-worthy
#   condition is the lane DELIVERING NOTHING: StoryWarmSuccess is emitted
#   UNCONDITIONALLY once per hourly warmer run (story_warmer.py — explicit 0
#   on an all-fail run, absent when the lane never ran), so
#   Sum(StoryWarmSuccess) <= 0 over a bucket == "the lane produced nothing",
#   and treat_missing_data=breaching makes silence itself breach (dead-man
#   semantics: absence IS the signal).
#
# SAMPLING (AL-5 anchor-drift scar honoured): emission is hourly (:19-:21).
#   period=7200 makes every bucket span TWO emission slots, so a single
#   missed hour can never empty a bucket; 2-of-2 means a page requires
#   ~2-4h of genuine lane silence. 7-day replay of this exact config:
#   ZERO zero-valued buckets (min hourly Sum 200), seven single-hour gaps
#   all absorbed, and exactly ONE would-have-paged event — the real 10h
#   emission silence 2026-08-12T10:21Z-20:21Z. One true positive, zero
#   false positives, zero flap.
#
# ENVIRONMENT DIMENSION READS "staging" ON PURPOSE (drift, documented not
#   hidden): the PRODUCTION warmer Lambda (autom8-asana-cache-warmer,
#   AUTOM8Y_ENV=production, ASANA_CW_NAMESPACE=autom8y/cache-warmer) does not
#   set ASANA_CW_ENVIRONMENT, so ObservabilitySettings.environment falls back
#   to its "staging" default (settings.py:793-795) and every StoryWarm series
#   the production lane writes carries environment=staging. This alarm watches
#   the series the lane ACTUALLY WRITES. Fixing the label is the
#   workflows-env-tag-drift class — a Lambda env change + redeploy, NOT this
#   cure's scope. If that fix lands, re-point this dimension in the same PR.
#
# ROUTING (fleet dual-route doctrine, autom8y terraform
#   scheduling_stratum_producer_alarms.tf:174-181): BOTH topics on BOTH
#   action lists — platform-alerts (notify tier: Slack lambda + email) AND
#   platform-sre-sev1 (paging tier: live SMS + email subscribers, verified
#   2026-08-14) — so a recovery also notifies both tiers. AlarmName follows
#   the fleet SEV-1 contract (autom8y-<service>-<class>) so PagerDuty-side
#   event orchestration can route on the prefix if/when armed there.
#   Response runbook: autom8y repo
#   docs/reliability/runbooks/RUNBOOK-platform-sre-sev1-paging-response.md.
#
# STATUS: CODE-OF-RECORD, CLI-applied (the F-1 pattern — this tf tree has no
#   wired apply pipeline; the sibling warmer_cache_degraded_alarm.tf documents
#   the same posture). Applied 2026-08-14 via `aws cloudwatch put-metric-alarm`
#   byte-matched to the values below; synthetic ALARM transition fired to the
#   pager and reset the same day (receipts in the nightly-smoke-resurrection
#   session H-1 handoff). When an apply path lands, IMPORT the live resource:
#
#     terraform import 'aws_cloudwatch_metric_alarm.story_warm_dead' \
#       autom8y-asana-story-warm-dead
# ============================================================================

variable "story_warm_dead_notify_topic_arn" {
  description = "Notify-tier SNS topic (Slack lambda + email). The live fleet route."
  type        = string
  default     = "arn:aws:sns:us-east-1:696318035277:autom8y-platform-alerts"
}

variable "story_warm_dead_page_topic_arn" {
  description = <<-EOT
    Paging-tier SNS topic (fleet-shared SEV-1). LIVE SMS + email subscribers
    verified 2026-08-14 — every ALARM/OK transition on this alarm reaches a
    human's phone. Do not point test alarms here.
  EOT
  type        = string
  default     = "arn:aws:sns:us-east-1:696318035277:autom8y-platform-sre-sev1"
}

resource "aws_cloudwatch_metric_alarm" "story_warm_dead" {
  alarm_name        = "autom8y-asana-story-warm-dead"
  alarm_description = "SEV-1 dead-man on the asana story-warm lane: Sum(StoryWarmSuccess) <= 0 (or the metric absent) for 2 consecutive 2h buckets == the lane has delivered NOTHING for ~2-4h — warmer dead, schedule off, or every warm failing. NOT a failure-count alarm (StoryWarmFailure is routinely nonzero; see code-of-record header). Dimension environment=staging is the documented label drift of the PRODUCTION lane (ASANA_CW_ENVIRONMENT unset -> staging default), not a staging alarm. Dual-routed: platform-alerts (notify) + platform-sre-sev1 (PAGES A HUMAN: live SMS). Runbook: RUNBOOK-platform-sre-sev1-paging-response.md (autom8y repo). RB: re-enable the warmer schedule / roll back the last warmer deploy; verify with the next hourly StoryWarmSuccess datapoint."

  namespace   = "autom8y/cache-warmer"
  metric_name = "StoryWarmSuccess"
  dimensions = {
    environment = "staging" # production lane's drifted label — see header
  }
  statistic = "Sum"

  comparison_operator = "LessThanOrEqualToThreshold"
  threshold           = 0
  period              = 7200
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "breaching" # dead-man: silence IS the signal

  alarm_actions = [
    var.story_warm_dead_notify_topic_arn,
    var.story_warm_dead_page_topic_arn,
  ]
  ok_actions = [
    var.story_warm_dead_notify_topic_arn,
    var.story_warm_dead_page_topic_arn,
  ]
}

output "story_warm_dead_alarm_name" {
  description = "The StoryWarm dead-man SEV-1 alarm name."
  value       = aws_cloudwatch_metric_alarm.story_warm_dead.alarm_name
}
