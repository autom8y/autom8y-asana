# ============================================================================
# F-1 -- warmer cache-degraded-mode listener (F1a cert LOW advisory, TS-1)
# ============================================================================
#
# Source of truth: F1a warmer-redis-fix cert (PR #257 / b3da9d8c) LOW advisory
#   + .ledge/reviews/WATCH-f1a-warmers-first-activation-2026-07-21.md §12/§13.
#
# WHAT: a CloudWatch Logs metric filter on each of the three warmer log groups
#   matching the structured ERROR event `cache_degraded_mode` (redis.py, added
#   by PR #257 as the "never-silent companion" to the redis-extra packaging
#   fix), rolled up into ONE alarm -> autom8y-platform-alerts. A warmer in
#   degraded mode runs a NO-OP cache: hierarchy-warm banking is lost at process
#   death and large gap sets never converge. This listener makes that condition
#   loud. It is QUIET WHEN HEALTHY: with `redis` importable the event is never
#   emitted, the metric stays missing, and treat_missing_data=notBreaching keeps
#   the alarm in OK.
#
# STATUS: LIVE via interactive-admin CLI apply 2026-07-21 (`aws logs
#   put-metric-filter` x3 + `aws cloudwatch put-metric-alarm`), receipted at
#   .ledge/reviews/RECEIPT-warmer-redis-fix-deploy-2026-07-21.md. This file is
#   the CODE-OF-RECORD, not (yet) the apply substrate: the asana tf tree has NO
#   wired apply pipeline and NO backend/state (the sibling observability_alarms.tf
#   suite AL-1..AL-4 is likewise authored-un-applied). When an apply path lands,
#   IMPORT the already-live resources rather than re-creating them:
#
#     terraform import 'aws_cloudwatch_metric_alarm.warmer_cache_degraded_mode' \
#       asana-F1-warmer-cache-degraded-mode
#     terraform import \
#       'aws_cloudwatch_log_metric_filter.warmer_cache_degraded["/aws/lambda/autom8-asana-cache-warmer"]' \
#       '/aws/lambda/autom8-asana-cache-warmer:asana-warmer-cache-degraded-mode'
#     # ...repeat for -bulk and -section (log_group:filter_name)
#
# The values below are byte-matched to the live CLI-applied resources so an
# import produces a clean (zero-diff) plan.
# ============================================================================

variable "warmer_cache_degraded_topic_arn" {
  description = <<-EOT
    SNS topic the F-1 warmer cache-degraded alarm notifies. Defaults to the live
    autom8y-platform-alerts topic (confirmed subs: autom8-slack-alert Lambda +
    email). This is a watch-only advisory (TS-1); notBreaching keeps it quiet
    when the cache is healthy.
  EOT
  type        = string
  default     = "arn:aws:sns:us-east-1:696318035277:autom8y-platform-alerts"
}

variable "warmer_log_groups" {
  description = <<-EOT
    The three warmer-lane Lambda log groups. All three share the wired image and
    the `cache-warmer` lane marker; -section is dormant (0 stored bytes, DISABLED
    schedule) but is included so a future enablement is covered by construction.
  EOT
  type        = set(string)
  default = [
    "/aws/lambda/autom8-asana-cache-warmer",
    "/aws/lambda/autom8-asana-cache-warmer-bulk",
    "/aws/lambda/autom8-asana-cache-warmer-section",
  ]
}

# One metric filter per warmer log group. All publish to the SAME metric with no
# distinguishing dimension, so the single alarm below fires on degraded mode in
# ANY warmer. Pattern selects the top-level structured event name (asana warmer
# logs are structlog JSON: `event` at top level, kwargs nested under `extra`).
resource "aws_cloudwatch_log_metric_filter" "warmer_cache_degraded" {
  for_each = var.warmer_log_groups

  name           = "asana-warmer-cache-degraded-mode"
  log_group_name = each.value
  pattern        = "{ $.event = \"cache_degraded_mode\" }"

  metric_transformation {
    name      = "CacheDegradedMode"
    namespace = "Autom8y/AsanaWarmerCache"
    value     = "1"
    # No default_value: only a match emits a datapoint, so the metric is absent
    # (not 0) when healthy -> pairs with treat_missing_data=notBreaching.
  }
}

resource "aws_cloudwatch_metric_alarm" "warmer_cache_degraded_mode" {
  alarm_name        = "asana-F1-warmer-cache-degraded-mode"
  alarm_description = "F-1 (F1a cert LOW advisory, TS-1 watch-only): a warmer Lambda entered cache degraded mode (event=cache_degraded_mode, ERROR, redis import/connection failed => no-op cache => hierarchy banking lost, gap sets never converge). Fires on ANY warmer (cache-warmer/-bulk/-section). Quiet when healthy (redis imports => event never emitted). Source: PR#257 redis.py loud degraded announcement; metric filters on the 3 warmer log groups. RB: revert b3da9d8c + redeploy, or rebuild image with the redis extra."

  namespace   = "Autom8y/AsanaWarmerCache"
  metric_name = "CacheDegradedMode"
  statistic   = "Sum"

  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.warmer_cache_degraded_topic_arn]
  # ok_actions intentionally omitted: watch-only advisory, we care about the
  # breach, not every INSUFFICIENT_DATA->OK settle.

  depends_on = [aws_cloudwatch_log_metric_filter.warmer_cache_degraded]
}

output "warmer_cache_degraded_alarm_name" {
  description = "The live F-1 warmer cache-degraded alarm name."
  value       = aws_cloudwatch_metric_alarm.warmer_cache_degraded_mode.alarm_name
}
