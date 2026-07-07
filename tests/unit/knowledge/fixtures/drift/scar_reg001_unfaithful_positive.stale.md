# Unfaithful positive-control fixture — DELIBERATELY STALE.
# Purpose: RESOLVED appears on the same line but strikethrough is stripped.
# The detector MUST reject this (DRIFT), proving it bites the full predicate
# (open-status token outside strikethrough), not just the presence of RESOLVED.
#
# This is the discriminating-canary: a naive detector that only checks for RESOLVED
# would incorrectly pass this fixture GREEN. Our detector strips strikethrough first
# and checks for bare open-status tokens, so this correctly → DRIFT.

## Outstanding Issues

- SCAR-REG-001: Production blocker — sequential placeholder GIDs unverified against live Asana API RESOLVED
