---
name: radar
description: "Cross-reference .know/ files to surface codebase opportunities and optionally challenge knowledge accuracy. Use when: assessing codebase health, finding work opportunities, validating .know/ accuracy. Triggers: radar, opportunities, health check, challenge knowledge."
argument-hint: "[--challenge <domain>] [--json] [--force]"
allowed-tools: Bash, Read, Write, Glob, Grep, Task, Skill, AskUserQuestion
model: opus
---

# /radar -- Knowledge Radar

Cross-references `.know/` files to surface actionable codebase opportunities and optionally challenge knowledge accuracy via adversarial theoros modes.

## Context

This dromenon runs in the main thread (requires Task tool for theoros dispatch). It reads `.know/` files as input — it does not observe the raw codebase directly. The Argus Pattern requires main-thread execution because agents cannot spawn agents.

Two modes:
- **Default**: Signal analysis across all 7 radar domains → opportunities ranked by severity and confidence
- **`--challenge <domain>`**: Adversarial challenge of a specific `.know/` file → contradiction report

## Pre-flight

### Parse arguments

- `--challenge <domain>`: If present, enter Challenge Mode (see below). Must be followed by a domain name (e.g., `--challenge architecture`).
- `--json`: Emit JSON to stdout instead of (or in addition to) markdown output. Can combine with either mode.
- `--force`: Skip staleness prompt. Proceed with whatever `.know/` files exist even if stale.

### If Challenge Mode

Jump to **Challenge Mode** section. Do not run signal analysis.

### If Default Mode

1. **Verify .know/ has content**:
   - `Glob(".know/*.md")`
   - If no files found: ERROR — "No `.know/` files found. Run `/know --all` first to generate codebase knowledge."
   - STOP.

2. **Read frontmatter from each .know/ file**:
   - For each file found, `Read()` the file (limit=20 lines to capture frontmatter).
   - Extract `domain`, `generated_at`, `expires_after`, `confidence` fields.
   - Record which files have complete frontmatter vs. missing/malformed fields.

3. **Detect stale files (unless --force)**:
   - For each file: parse `generated_at` (ISO 8601) and `expires_after` (e.g., `"7d"`).
   - Compute expiry date = `generated_at` + `expires_after` duration.
   - If expiry date < now: mark as stale.
   - If any stale files found AND `--force` is NOT set:
     - `AskUserQuestion("These .know/ domains are stale: {list of stale domain names}. Refresh before analysis? (yes/no)")`
     - If user answers yes: dispatch `/know --force {domain}` for each stale domain (run as Bash command: `ari know {domain} --force` or equivalent). Wait for completion before proceeding.
     - If user answers no: proceed with stale files as-is. Note in report which domains were stale at analysis time.

4. **Ensure output directories exist**:
   - `Bash("mkdir -p .know .ledge/reviews")`

## Phase 1: Criteria Loading

Load the pinakes skill to access the domain registry:

```
Skill("pinakes")
```

Filter domains with `scope: radar` from the registry. The 7 radar signal domains are:
- `radar-confidence-gaps`
- `radar-staleness`
- `radar-unguarded-scars`
- `radar-constraint-violations`
- `radar-convention-drift`
- `radar-architecture-decay`
- `radar-recurring-scars`

For each radar signal domain, read its criteria file:
```
Read(".channel/skills/pinakes/domains/{domain}.md")
```

Store all loaded criteria keyed by domain name. This content is injected into each theoros dispatch prompt in Phase 2.

Also read the relevant `.know/` file bodies you will need per signal (to inject into theoros prompts):
- `architecture`, `conventions`, `scar-tissue`, `design-constraints`, `test-coverage` — read all that exist.
- Track which files were successfully read (for `know_files_read` frontmatter field).

## Phase 2: Signal Analysis — Argus Pattern

> "One body, a hundred eyes, nothing unseen." — All 7 theoros dispatched in parallel.

**YOU MUST USE THE TASK TOOL TO DISPATCH THEOROS SUBAGENTS.** Do NOT analyze the `.know/` files yourself. Do NOT read them and write opportunities directly. Each signal domain MUST be delegated to a theoros subagent via `Task(subagent_type="theoros", ...)`.

**ALL 7 Task calls MUST appear in a SINGLE response block.** This is the Argus Pattern — parallel dispatch, concurrent analysis. Do NOT dispatch sequentially.

For each radar signal domain, construct a Task prompt using the template below. Inject the full criteria file content AND the relevant `.know/` file content that the signal requires.

### Signal-to-Input Mapping

| Signal Domain | .know/ Files Needed |
|---|---|
| `radar-confidence-gaps` | All `.know/` frontmatter (inject all frontmatter you collected in pre-flight) |
| `radar-staleness` | All `.know/` frontmatter (same) |
| `radar-unguarded-scars` | `.know/scar-tissue.md` body + `.know/test-coverage.md` body |
| `radar-constraint-violations` | `.know/design-constraints.md` body |
| `radar-convention-drift` | `.know/conventions.md` body |
| `radar-architecture-decay` | `.know/architecture.md` body |
| `radar-recurring-scars` | `.know/scar-tissue.md` body |

### Dispatch Prompt Template

```
Task(subagent_type="theoros", prompt="
## Radar Signal Analysis: {signal_domain}

You are running a RADAR SIGNAL ANALYSIS, not a standard codebase audit.

Your input is pre-read .know/ file content (structured knowledge about the codebase), NOT raw source code. Your job is to apply the signal criteria to this knowledge and identify opportunities — specific, actionable findings backed by evidence in the .know/ content.

### Signal Criteria

{full_criteria_file_content}

### Input: .know/ Content

{inject the relevant .know/ file content(s) for this signal as specified in the Signal-to-Input Mapping above}

### Your Task

Apply the signal criteria to the provided .know/ content. For each finding:

1. Identify the specific package, domain, or file that the signal fires on.
2. Assess severity: HIGH | MEDIUM | LOW (use the opportunity schema severity scale).
3. Assess confidence: source_confidence × evidence_strength (use the opportunity schema formula).
4. Cite specific evidence from the .know/ content (file paths, line numbers, quoted claims).
5. Draft a suggested action in consultant-style prose — explain the issue, name the rite or approach, state the expected outcome. Do NOT produce machine enums or structured routing tables.
6. Suppress findings with confidence < 0.40. Note the count of suppressed findings in your output.

### Output Format

Produce a structured list of findings. For each finding:

```
FINDING:
  Signal: {signal_domain}
  Package/Target: {specific package or file or domain name}
  Severity: HIGH | MEDIUM | LOW
  Confidence: {0.00-1.00} ({source_confidence} × {evidence_strength_name} {evidence_strength_multiplier})
  Evidence:
    - {specific reference from .know/ content}
    - {additional reference if applicable}
  Suggested Action: {consultant-style prose}
```

After all findings, produce a summary line:
```
SUMMARY: {N} findings | {high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW | {suppressed_count} suppressed (confidence < 0.40)
```

If no findings: output `NO FINDINGS` and a one-sentence explanation of why.
")
```

## Phase 3: Synthesis

After ALL 7 theoros agents return (wait for all parallel dispatches):

### 3a. Collect and parse findings

For each theoros output:
- Parse all `FINDING:` blocks into structured records.
- Parse the `SUMMARY:` line for counts.
- Track which signals produced findings and which did not.

### 3b. Deduplicate by package

When multiple signals flag the same package or file:
1. Group all findings for that package into one opportunity entry.
2. Set severity to the HIGHEST among contributing signals.
3. Set confidence to the MINIMUM among contributing signals (conservative).
4. List all contributing signals in the Signal field, comma-separated.
5. Combine all evidence items from all contributing signals.
6. Write one Suggested Action addressing all signals together.

Reference the deduplication rules in `radar/schemas/report.md` for exact behavior.

### 3c. Prioritize

Sort all (deduplicated) opportunities:
1. Severity descending: HIGH → MEDIUM → LOW.
2. Within same severity: confidence descending.
3. Within same severity and confidence: signal name alphabetically.

### 3d. Assign OPP-NNN identifiers

Assign sequential identifiers `OPP-001`, `OPP-002`, ... in priority order (after sorting).

### 3e. Generate advisory routing (consultant-style)

For high-impact findings or clusters, generate a paragraph of advisory prose. This is NOT a structured routing table. Write it like a trusted advisor:

> "The `internal/cmd/sync` package shows convergent signals — unguarded scars, convention drift, and architecture boundary concerns. This is a strong candidate for a focused hygiene session, potentially followed by an arch review if the boundary violations are confirmed. Addressing the scar coverage gap first would reduce regression risk before any refactoring."

This prose is optional and should only be generated when 3+ signals converge on the same area or when a HIGH finding has an non-obvious remediation path.

## Phase 4: Output

### 4a. Build the report

Assemble the full report following the `.know/radar.md` body template in `radar/schemas/report.md`:

```
# Knowledge Radar — {YYYY-MM-DD}

## Summary
{2–3 sentence overview: opportunity count, which signals fired, single most critical finding}

## Opportunities
{All OPP-NNN entries in priority order, using opportunity.lego.md format}

## Signals with No Findings
{Signals that ran but produced zero findings, one line each}

## Suppressed Findings
{If any were suppressed for low confidence, list count and signals. Omit section if none.}

## Methodology
- **Signals evaluated**: {comma-separated list}
- **Source files read**: {comma-separated list of .know/ domains}
- **Deduplication**: Grouped by package; multi-signal entries combined
- **Priority ordering**: Severity (HIGH → LOW) then confidence (descending)
- **Run date**: {YYYY-MM-DD}
```

Build frontmatter following `radar/schemas/report.md`:

```yaml
---
domain: radar
generator: radar
generated_at: "{current ISO 8601 UTC timestamp}"
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
  - {list of domains successfully read}
opportunity_count: {N}
high_count: {N}
medium_count: {N}
low_count: {N}
---
```

### 4b. Write and verify .know/radar.md

```
Write(".know/radar.md", frontmatter + body)
Read(".know/radar.md", limit=30)
```

Confirm frontmatter fields are present. Confirm opportunity sections exist.

### 4c. Archive to .ledge/reviews/

```
Write(".ledge/reviews/RADAR-{YYYY-MM-DD}.md", same_content)
```

If a file already exists at that path (same-day second run): append counter `RADAR-{YYYY-MM-DD}-2.md`.

### 4d. Display summary to user

```
## Knowledge Radar Complete — {YYYY-MM-DD}

| Signal | Findings | Suppressed |
|--------|----------|------------|
| radar-confidence-gaps | {N} | {N} |
| radar-staleness | {N} | {N} |
| radar-unguarded-scars | {N} | {N} |
| radar-constraint-violations | {N} | {N} |
| radar-convention-drift | {N} | {N} |
| radar-architecture-decay | {N} | {N} |
| radar-recurring-scars | {N} | {N} |

**{total_count} opportunities found** ({high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW)

Top finding: [OPP-001] {title} ({severity}, confidence {value})

Full report: `.know/radar.md`
Archive: `.ledge/reviews/RADAR-{YYYY-MM-DD}.md`
```

### 4e. If --json flag

After the display summary, emit JSON to stdout using the shape defined in `radar/schemas/report.md`. Do NOT write JSON to disk.

---

## Challenge Mode (`--challenge <domain>`)

Entered when `--challenge <domain>` argument is present.

### Challenge Pre-flight

1. **Parse domain**: Extract the domain name argument (e.g., `architecture` from `--challenge architecture`).
2. **Verify .know/{domain}.md exists**:
   - `Glob(".know/{domain}.md")`
   - If not found: ERROR — "`.know/{domain}.md` not found. Run `/know {domain}` first to generate knowledge for this domain."
   - STOP.
3. **Read the challenged file**:
   - `Read(".know/{domain}.md")`
   - This is the INPUT being challenged — inject its full content into theoros dispatch prompts.

### Challenge Criteria Loading

Load the pinakes skill:
```
Skill("pinakes")
```

Look up available challenge domains for the requested domain:
- Check if `adversarial-{domain}` exists in the registry (scope: adversarial).
- Check if `dialectic-{domain}` exists in the registry (scope: dialectic).
- If NEITHER exists: ERROR — "No challenge criteria available for domain `{domain}`. Available challenge domains: {list all adversarial- and dialectic- domains from registry}."

For each that exists, read its criteria:
```
Read(".channel/skills/pinakes/domains/adversarial-{domain}.md")   # if exists
Read(".channel/skills/pinakes/domains/dialectic-{domain}.md")    # if exists
```

### Challenge Dispatch

Dispatch ALL available theoros for this domain in a SINGLE response block (parallel):

```
Task(subagent_type="theoros", prompt="
## Challenge Mode: {adversarial|dialectic}-{domain}

You are running an ADVERSARIAL CHALLENGE of a .know/ file. Your goal is to find evidence that CONTRADICTS claims in the challenged document.

### Challenge Criteria

{full_criteria_file_content}

### The Document Being Challenged

Below is the full content of `.know/{domain}.md`. This is what you are challenging.

---
{full .know/{domain}.md content}
---

### Your Task

Apply the challenge criteria above. Actively search for contradictions, not confirmations.

For each finding, produce:

```
CHALLENGE FINDING:
  Claim: {verbatim quote or close paraphrase from .know/{domain}.md, with section reference}
  Counter-Evidence:
    - {file path}:{line} — {specific contradiction}
    - {additional evidence if available}
  Contradiction Confidence: HIGH | MEDIUM | LOW
  Recommendation: Update knowledge | Fix code | Accept gap
  Rationale: {1-3 sentence consultant-style explanation}
```

After all findings, produce:
```
CHALLENGE SUMMARY: {N} contradictions found | {high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW | {N} claims checked
```

If no contradictions found: output `NO CONTRADICTIONS FOUND` with explanation. State how many claims were checked.
")
```

### Challenge Output

After theoros agents return:

1. Parse all `CHALLENGE FINDING:` blocks.
2. Assemble the challenge report following the template in `radar/schemas/report.md`.
3. Write the report:
   ```
   Write(".ledge/reviews/CHALLENGE-{domain}-{YYYY-MM-DD}.md", challenge_report_content)
   ```
4. Verify:
   ```
   Read(".ledge/reviews/CHALLENGE-{domain}-{YYYY-MM-DD}.md", limit=30)
   ```
5. Do NOT write to `.know/radar.md`. Challenge output goes to `.ledge/reviews/` only.
6. Display summary to user:

```
## Challenge Report: {domain} — {YYYY-MM-DD}

Challenge modes run: {list of adversarial-/dialectic- domains dispatched}
Contradictions found: {N} ({high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW)
Claims checked: {N}

{If contradictions found}: Top finding: {Finding 1 title} ({contradiction_confidence})

Full report: `.ledge/reviews/CHALLENGE-{domain}-{YYYY-MM-DD}.md`
```

7. If `--json` flag: emit JSON summary of challenge findings to stdout (not to disk). Use similar shape as the radar JSON schema but adapted for challenge findings.

---

## Error Handling

| Scenario | Action |
|----------|--------|
| No `.know/` files found | ERROR: "No `.know/` files found. Run `/know --all` first." STOP. |
| `.know/{domain}.md` not found (challenge mode) | ERROR: "`.know/{domain}.md` not found. Run `/know {domain}` first." STOP. |
| No challenge criteria for domain | ERROR listing available challenge domains. STOP. |
| Specific `.know/` file missing for a signal | Dispatch theoros without that input; note the gap in signal findings. Continue other signals. |
| Theoros dispatch fails | ERROR "Signal analysis failed for {domain}: {reason}". Continue other signals. |
| Theoros output unparseable | Use findings as raw text, note parsing failure in report methodology section. |
| `.ledge/reviews/` not writable | ERROR with directory path and permission details. |
| Archive collision (same-day second run) | Append counter: `RADAR-{YYYY-MM-DD}-2.md`. |

---

## Anti-Patterns

- **Analyzing .know/ files yourself instead of dispatching theoros**: You are the ORCHESTRATOR. Load criteria, dispatch theoros via Task tool, then synthesize their outputs. If you find yourself reading `.know/` files and writing opportunity entries directly, STOP — you are violating the dispatch pattern.
- **Dispatching theoros sequentially**: All 7 radar signal theoros MUST launch in a single response block. Sequential dispatch serializes what should be parallel analysis and produces slower, more context-exhausted results.
- **Including machine-actionable routing enums**: Routing is consultant-style prose. Do NOT produce `{rite: "hygiene", command: "/task ...", severity: "HIGH"}`. Write it as an advisor would speak it.
- **Writing to .know/radar.md during --challenge mode**: Challenge output belongs exclusively in `.ledge/reviews/CHALLENGE-{domain}-{date}.md`. Do not update the radar snapshot during a challenge run.
- **Running /know --force without user confirmation**: Staleness refresh is interactive. Always ask via AskUserQuestion before dispatching `/know --force`. The `--force` flag on `/radar` itself skips the prompt but never auto-refreshes knowledge silently.
- **Skipping .know/radar.md verification**: Always Read the output file after writing to confirm frontmatter and body are present.
- **Ignoring missing .know/ files for signals**: Log which files were missing, proceed with signals that have their input. A missing `test-coverage.md` should not abort `radar-confidence-gaps` analysis.
