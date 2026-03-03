---
name: radar-report-schema
description: "Full report format for /radar output including .know/radar.md schema, --json shape, archival format, and challenge report format. Use when: formatting radar reports, writing .know/radar.md, producing RADAR archival files, formatting challenge reports. Triggers: radar report, radar.md schema, radar json output, challenge report, RADAR archival."
user-invocable: false
---

# Schema: Radar Report

Standardized output formats for `/radar` runs and `/radar --challenge` runs.

## Report Types

| Type | Command | Output Location |
|------|---------|-----------------|
| **Radar Snapshot** | `/radar` | `.know/radar.md` (latest) |
| **Radar Archive** | `/radar` | `.ledge/reviews/RADAR-{YYYY-MM-DD}.md` |
| **Machine Output** | `/radar --json` | stdout (not written to disk) |
| **Challenge Report** | `/radar --challenge {domain}` | `.ledge/reviews/CHALLENGE-{domain}-{YYYY-MM-DD}.md` |

---

## `.know/radar.md` — Radar Snapshot

### Frontmatter Schema

```yaml
---
domain: radar
generator: radar
generated_at: "YYYY-MM-DDTHH:MM:SSZ"
expires_after: "7d"
signals_evaluated:
  - radar-confidence-gaps
  - radar-staleness
  - radar-unguarded-scars
  - radar-constraint-violations
  - radar-convention-drift
  - radar-architecture-decay
  - radar-recurring-scars
know_files_read:
  - architecture
  - conventions
  - scar-tissue
  - design-constraints
  - test-coverage
opportunity_count: {N}
high_count: {N}
medium_count: {N}
low_count: {N}
---
```

**Notes on frontmatter fields:**

- `domain: radar` — This is the radar meta-domain, not a theoros codebase domain.
- `generator: radar` — Marks this as produced by `/radar`, not by theoros. Consumers distinguish this from standard `.know/` files.
- `expires_after: "7d"` — Default staleness window. `/radar` itself will flag when this file is stale and ask whether to re-run.
- `know_files_read` — Lists only the `.know/` files that were successfully read during this run (excludes missing files).

### Body Template

```markdown
---
{frontmatter as above}
---

# Knowledge Radar — {YYYY-MM-DD}

## Summary

{2–3 sentence overview. State how many opportunities were found, which signals fired,
and what the single most critical finding is.}

## Opportunities

{Opportunity entries in priority order: HIGH first, then MEDIUM, then LOW.
Within each severity tier, order by confidence descending.
Use the OPP-NNN format defined in opportunity.lego.md.}

### [OPP-001] ...

### [OPP-002] ...

## Signals with No Findings

{List any of the 7 signals that ran but found nothing. One line each.}

- **radar-staleness**: All .know/ files within expiry window.
- **radar-convention-drift**: No drift detected in sampled files.

## Suppressed Findings

{If any low-confidence findings (< 0.40) were suppressed, list the count and signals here.
If none were suppressed, omit this section.}

{N} findings suppressed (confidence < 0.40): {signal names}.

## Methodology

- **Signals evaluated**: {comma-separated list of the 7 signals}
- **Source files read**: {comma-separated list of .know/ files}
- **Deduplication**: Grouped by package; multi-signal entries combined
- **Priority ordering**: Severity (HIGH → LOW) then confidence (descending)
- **Run date**: {YYYY-MM-DD}
```

---

## `.ledge/reviews/RADAR-{YYYY-MM-DD}.md` — Archive Format

The archive is a verbatim copy of `.know/radar.md` at time of run. No additional sections required.

**Naming**: `RADAR-{YYYY-MM-DD}.md` where the date is the `generated_at` date from frontmatter.

**If multiple radar runs happen on the same day**, append a counter: `RADAR-2026-03-02-2.md`.

---

## `--json` Output Shape

Emitted to stdout when `/radar --json` is invoked. Not written to disk.

```json
{
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "generator": "radar",
  "domain": "radar",
  "expires_after": "7d",
  "signals_evaluated": [
    "radar-confidence-gaps",
    "radar-staleness",
    "radar-unguarded-scars",
    "radar-constraint-violations",
    "radar-convention-drift",
    "radar-architecture-decay",
    "radar-recurring-scars"
  ],
  "know_files_read": ["architecture", "conventions", "scar-tissue", "design-constraints", "test-coverage"],
  "summary": "string — 1–2 sentences",
  "opportunities": [
    {
      "id": "OPP-001",
      "title": "string",
      "signal": "radar-unguarded-scars",
      "severity": "HIGH",
      "confidence": 0.72,
      "evidence": [
        {
          "file": "internal/sync/engine.go",
          "line": 142,
          "finding": "SCAR-004 defensive pattern with no test coverage"
        }
      ],
      "suggested_action": "string — full prose recommendation"
    }
  ],
  "signals_with_no_findings": ["radar-staleness", "radar-convention-drift"],
  "suppressed_count": 0
}
```

**Field types:**

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | ISO 8601 string | UTC timestamp of the run |
| `generator` | string | Always `"radar"` |
| `domain` | string | Always `"radar"` |
| `expires_after` | string | Duration string, e.g. `"7d"` |
| `signals_evaluated` | string[] | All signals that were run |
| `know_files_read` | string[] | `.know/` domain names read (without `.md`) |
| `summary` | string | 1–2 sentence executive summary |
| `opportunities` | Opportunity[] | Ordered: HIGH first, then confidence descending |
| `opportunities[].id` | string | `"OPP-NNN"` format |
| `opportunities[].signal` | string | One signal domain name (or comma-joined if deduplicated) |
| `opportunities[].severity` | enum | `"HIGH"`, `"MEDIUM"`, or `"LOW"` |
| `opportunities[].confidence` | float | 0.00–1.00 |
| `opportunities[].evidence` | Evidence[] | At least one element required |
| `opportunities[].evidence[].file` | string | Relative file path |
| `opportunities[].evidence[].line` | int \| null | Line number, null if not applicable |
| `opportunities[].evidence[].finding` | string | Specific finding at that location |
| `opportunities[].suggested_action` | string | Full prose — same content as markdown version |
| `signals_with_no_findings` | string[] | Signals that ran but produced zero opportunities |
| `suppressed_count` | int | Count of findings suppressed for low confidence |

---

## `.ledge/reviews/CHALLENGE-{domain}-{YYYY-MM-DD}.md` — Challenge Report

Produced by `/radar --challenge {domain}`.

### Template

```markdown
# Challenge Report: {domain} — {YYYY-MM-DD}

**Challenged File**: `.know/{domain}.md`
**Challenge Modes Run**: {advocatus | socratic | both}
**Run Date**: {YYYY-MM-DD}

## Executive Summary

{2–3 sentences. State whether the challenged knowledge file holds up, what the strongest
contradiction found was, and the overall recommendation.}

## Findings

{One section per finding. Each finding is a (claim, counter-evidence, confidence, recommendation) tuple.}

### Finding {N}: {short title}

**Claim** (from `.know/{domain}.md`):
> {verbatim quote or close paraphrase from the knowledge file, with section reference}

**Counter-Evidence**:
- `{file path}:{line}` — {specific contradiction found}
- `{file path}:{line}` — {supporting evidence for contradiction}

**Contradiction Confidence**: {HIGH | MEDIUM | LOW}

| Level | Meaning |
|-------|---------|
| HIGH | Direct code evidence directly contradicts the claim |
| MEDIUM | Circumstantial evidence suggests the claim may be outdated or incomplete |
| LOW | Logical tension or unstated assumption — not a direct contradiction |

**Recommendation**: {one of: Update knowledge | Fix code | Accept gap}

{1–3 sentences of consultant-style prose explaining which action to take and why.}

---

## No Contradictions Found

{If the challenge found nothing to contradict, replace the Findings section with this:}

No contradictions found. The claims in `.know/{domain}.md` are consistent with current
codebase evidence across {N} checked claims.

## Methodology

- **Challenge modes**: {list of modes run: advocatus-{domain}, socratic-{domain}}
- **Source file**: `.know/{domain}.md` (generated: {generated_at date})
- **Claims checked**: {N}
- **Contradictions found**: {N}
- **Run date**: {YYYY-MM-DD}
```

### Challenge Recommendation Values

| Value | When to Use |
|-------|-------------|
| `Update knowledge` | The code is correct; the `.know/` file is stale or wrong |
| `Fix code` | The `.know/` file correctly describes intent; the code violates it |
| `Accept gap` | The tension is known and intentional; no action needed but document why |

---

## Priority Ordering Rules

Applied to opportunities within the `.know/radar.md` body and the `--json` output:

1. **Primary sort**: Severity descending — HIGH before MEDIUM before LOW.
2. **Secondary sort**: Confidence descending within each severity tier.
3. **Tie-breaking**: Within the same severity and confidence, order by signal alphabetically.

This ordering ensures the most actionable and certain findings appear first.

## Deduplication Rules

When the same package or file is flagged by multiple signals:

1. Group all signal findings for that package into one OPP entry.
2. Set severity to the highest severity among contributing signals.
3. Set confidence to the minimum confidence among contributing signals (conservative).
4. List all contributing signals in the Signal field (comma-separated).
5. Combine all evidence items from all signals into one Evidence list.
6. Write one Suggested Action addressing all signals together.

**Example**: If `internal/cmd/sync` is flagged by both `radar-unguarded-scars` (HIGH, 0.80) and
`radar-convention-drift` (MEDIUM, 0.65), the merged entry is: severity=HIGH, confidence=0.65,
signal=`radar-unguarded-scars, radar-convention-drift`.

## Related

- [opportunity.lego.md](opportunity.lego.md) — OPP-NNN entry format
- [../INDEX.dro.md](../INDEX.dro.md) — /radar dromenon
- [../../pinakes/schemas/report-format.lego.md](../../pinakes/schemas/report-format.lego.md) — Theoria report format (parallel system)
