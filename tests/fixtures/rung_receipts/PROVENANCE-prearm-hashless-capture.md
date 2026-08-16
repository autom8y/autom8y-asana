# PROVENANCE — asr_prearm_hashless_report_posted.jsonl

Captured 2026-08-16 (seam coc-reattest-seam, session-20260816-103254-f12e8f75)
per DESIGN-r2-r3-detection-lanes-2026-08-16.md recommendation O3-1: the R-3
hash-presence deadman's RED fixture is REAL production bytes — genuinely
hashless pre-arm `report_posted` events — and ASR's 30-day log retention ages
them out ~2026-09-12. Captured before expiry, independent of build timing.

- Source: CloudWatch `/aws/lambda/autom8y-account-status-recon`, raw
  `aws logs filter-log-events` (never Logs Insights — R-4 fence), window
  2026-08-14T00:00:00Z → 2026-08-14T20:10:00Z (strictly pre-arm; the arming
  deploy completed ~2026-08-14T20:05Z, first hashed pair 2026-08-15T00:01Z).
- Contents: first 2 events of the window, verbatim message JSON, one per line.
  Both `has("content_hash") == false` (key ABSENT, not null — matching
  `{ $.content_hash NOT EXISTS }` filter shape). Invocations
  `01177745-0759-4874-8e07-9fbf2eef5b18` (00:01:01Z) and
  `2d9bb8a3-f026-4ab3-bb56-00fde60a83cd` (04:01:07Z).
- Intended use: read-only `aws logs test-metric-filter` proof of the R-3
  metric filter, and the discriminating RED side of its two-sided alarm proof.
  No secret material present (channel, counts, ids only — CR-5 clean).
