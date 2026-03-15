---
name: know
description: "Generate persistent codebase knowledge via theoros observation. Produces .know/{domain}.md and .know/feat/{slug}.md with schema-validated frontmatter and structured knowledge sections."
argument-hint: "[domain|--all|--scope=feature] [--force] [--expires=DURATION] [--census] [--feature=SLUG] [--root=PATH]"
allowed-tools: Bash, Read, Write, Glob, Grep, Task, Skill
model: opus
---

# /know -- Codebase Knowledge Generator

Dispatches theoros to observe and document codebase architecture, producing persistent `.know/` reference files that any CC agent can consume for codebase context. Supports two modes: **codebase domains** (default) and **feature knowledge** (`--scope=feature`).

## Context

This command runs in the main thread (requires Task tool for theoros dispatch). It generates `.know/` files at the project root. The Argus Pattern requires main-thread execution because agents cannot spawn agents — only the main thread has Task tool access.

## Platform Constraint: Read Before Write

**The Claude Code Write tool WILL FAIL if you attempt to write to an existing file without first reading it via the Read tool in the current conversation.** This is a hard platform constraint, not optional.

Before EVERY `Write()` call in this dromenon, you MUST check whether the target file already exists and, if so, `Read()` it first. This applies even when `--force` is set -- force controls whether to skip expiry checks, it does NOT exempt you from the read-before-write requirement. The three write points where this matters:
1. Phase 3 step 3: `Write(".know/{domain}.md", ...)` -- read existing file if it exists
2. Census step 3: `Write(".know/feat/INDEX.md", ...)` -- read existing file if it exists
3. Per-feature step 4: `Write(".know/feat/{slug}.md", ...)` -- read existing file if it exists

Some code paths already read the file for other reasons (Phase 0 time-only, Phase 2a incremental). The critical gap is the **full queue path** (Phase 2b), where `--force` regenerates an existing file from scratch -- you still must `Read()` it before `Write()`.

## Scope Routing

**If `--scope=feature` is present**: Skip to [Feature Knowledge Flow](#feature-knowledge-flow---scope-feature). The entire codebase domain pipeline below does NOT apply.

**Otherwise**: Continue with the codebase domain pipeline below (default behavior).

---

## Codebase Domain Pipeline (Default)

## Pre-flight

1. **Parse arguments**:
   - `domain`: Optional. Default: `"architecture"`. Must be a registered pinakes domain with `codebase` scope.
   - `--all`: Generate ALL codebase-scoped domains. Overrides `domain` argument. Uses **Argus Pattern** (parallel theoros dispatch).
   - `--force`: Skip expiry check, regenerate even if current.
   - `--expires=DURATION`: Override default expiry (e.g., `--expires=14d`). Default: `"7d"`.
   - `--root=PATH`: Scoped generation target directory (monorepo support). When set:
     - Validate: path exists and is under project root. ERROR if not: "Root path '{path}' does not exist" or "Root path '{path}' is not under project root".
     - Output directory becomes `{root}/.know/` instead of project root `.know/`
     - Theoros observation scope is constrained to `{root}/` and its subtree
     - `source_scope` globs resolve relative to `{root}/` (e.g., `./internal/**/*.go` scopes to `{root}/internal/`)
     - The `ari knows --delta` call becomes `ari knows --scope-dir={root} --delta -o json`
     - Criteria inheritance: check `{root}/.know/criteria/` first (local override); fall back to project root `.know/criteria/`
     - Pinakes registry is always loaded from global (framework-level, not service-level)

2. **Load domain registry**:
   - Load pinakes skill: `Skill("pinakes")`
   - Read pinakes INDEX to find the Domain Registry table
   - If `--all`: collect ALL domains with scope `codebase` from the registry
   - If single domain: verify requested domain appears in the table with scope `codebase`
   - If not found: ERROR "Domain '{domain}' not registered in pinakes or not codebase-scoped. Available codebase domains: {list}"
   - **Scan for satellite-authored criteria**: Check if `{knowDir}/criteria/` exists and contains any `*.md` files (where `{knowDir}` is `{root}/.know/` when `--root` is set, otherwise `.know/`). If it does, read each file and merge its domain entry into the registry alongside the pinakes domains. Each criteria file follows the same format as pinakes domain files. If `{knowDir}/criteria/` does not exist, fall back to `.know/criteria/` (project root) when `--root` is set. If neither exists or both are empty, continue normally with only pinakes domains.

2.5. **Discover land files** (mapping-based):
   - Define the land-to-know mapping (hardcoded -- these are design decisions, not discovery):
     ```
     LAND_MAP = {
       "architecture":       [".sos/land/initiative-history.md"],
       "conventions":        [".sos/land/workflow-patterns.md"],
       "design-constraints": [".sos/land/initiative-history.md"],
       "scar-tissue":        [".sos/land/scar-tissue.md"],
       "test-coverage":      [".sos/land/workflow-patterns.md"],
     }
     ```
   - For each domain in the generation set (from step 2):
     - Look up `LAND_MAP[domain]`. If no entry exists, this domain has no land input. Skip.
     - For each land file path listed in the mapping, check if it exists:
       ```
       Bash("test -f {land_path} && echo 'exists' || echo 'missing'")
       ```
     - For each existing land file, read its content:
       ```
       Read("{land_path}")
       ```
     - If land file content exceeds 20,000 characters, truncate to the first 20,000 characters and append:
       `\n\n[Land content truncated at 20,000 characters. Full file: {land_path}]`
     - If land file content is empty after reading, treat as absent (skip this file).
     - Concatenate all non-empty land file contents for this domain, separated by:
       `\n\n---\n\n### Land Source: {land_path}\n\n`
     - Compute SHA-256 hash of the concatenated raw (untruncated) content of all existing land files:
       ```
       Bash("cat {space-separated existing land_paths} | shasum -a 256 | cut -d' ' -f1")
       ```
     - Store per domain: `land_file_content` (possibly truncated concatenation), `land_hash` (hash of raw content), `land_sources` (list of paths that exist).
   - Store the per-domain results in a `land_files` map keyed by domain name. Domains with no existing land files have no entry in the map.
   - Report: "Land files found: {domain}: {list of existing land paths}" for each matched domain, or "No land files found for any domain."

3. **Build generation queue** (uses `ari knows --delta` for change analysis):
   - First, check each domain for non-delta conditions:
     - If `{knowDir}/{domain}.md` does not exist: ADD to **full** queue (skip delta for this domain)
     - If `--force` is set: ADD to **full** queue (skip delta for this domain)
   - Then, for ALL remaining domains in a **single batch call**:
     - If `--root` is set: Run: `Bash("ari knows --scope-dir={root} --delta -o json")`
     - Otherwise: Run: `Bash("ari knows --delta -o json")`
     - This returns a JSON object with a `domains` array containing ALL domain deltas. One call, not N calls. The CLI caches git operations internally so overlapping source scopes don't cause redundant git subprocess invocations.
     - Parse the batch result and route each domain entry by its `mode` field:
       - `mode == "skip"`: report "Knowledge for '{domain}' is current" and SKIP
       - `mode == "time-only"`: ADD to **time-only** queue
       - `mode == "incremental"` AND `force_full == false`: ADD to **incremental** queue
       - `mode == "full"` OR `force_full == true`: ADD to **full** queue
   - If all queues are empty: report "All domains are current. Use --force to regenerate." and STOP.
   - Report queues: "Time-only refresh: {N}, Incremental update: {N}, Full regeneration: {N}, Skipped: {N}"
   - Store the delta JSON for each incremental domain (used in Phase 2a for change context).

4. **Compute source_hash**:
   - Run: `git rev-parse --short HEAD`
   - Store result for frontmatter injection.

5. **Ensure .know/ directory exists**:
   - If `--root` is set: Run: `mkdir -p {root}/.know`
   - Otherwise: Run: `mkdir -p .know`

## Phase 0: Time-Only Refresh

Process the **time-only** queue first. These domains have no code changes since the last analysis — only the time expiry triggered. Zero theoros cost, zero quality risk.

For EACH domain in the time-only queue:

1. **Read the existing file**:
   ```
   Read(".know/{domain}.md")
   ```

2. **Update frontmatter only**:
   - Set `generated_at` to current ISO 8601 UTC timestamp
   - Set `source_hash` to the git short SHA from pre-flight step 4
   - Set `update_mode: "time-only"`
   - Reset `incremental_cycle` to `0` (time-only is not an incremental update)
   - Preserve ALL other frontmatter fields and the ENTIRE body unchanged

3. **Write the file**:
   ```
   Write(".know/{domain}.md", updated_frontmatter + original_body)
   ```

4. **Report**: "Refreshed '{domain}' (time-only, no code changes)"

After processing all time-only domains, continue to Phase 1 for incremental and full queues.

If ONLY time-only domains were queued (incremental and full queues are empty), skip directly to Phase 4: Report.

## Phase 1: Criteria Loading

For EACH domain in the generation queue:

1. Read the domain criteria file:
   ```
   Read(".claude/skills/pinakes/domains/{domain}.md")
   ```

2. Extract the full criteria content for injection into the theoros dispatch prompt.

Store all loaded criteria keyed by domain name.

## Phase 2a: Incremental Theoros Dispatch

Process the **incremental** queue. These domains have code changes within scope, but the delta is small enough that theoros can update the existing knowledge rather than re-reading the entire codebase.

**YOU MUST USE THE TASK TOOL.** Do NOT update knowledge yourself.

**If multiple incremental domains**: Launch ALL theoros agents in a SINGLE response block (Argus Pattern).

For each domain in the incremental queue:

1. **Gather change context**:
   - Read the existing `.know/{domain}.md` (this is the current knowledge to update)
   - The delta JSON from Pre-flight Step 3 contains the ChangeManifest (files changed, commit log, delta stats)
   - Run `Bash("git diff {from_hash}..{to_hash} -- {space-separated in-scope modified files}")` to get per-file diffs
   - If total diff exceeds 100K characters, truncate to the first 100K with a note "(truncated)"

2. **Dispatch incremental theoros**:

```
Task(subagent_type="theoros", prompt="
## Incremental Knowledge Update: {domain}

You are UPDATING an existing knowledge reference document, not creating one from scratch. Your goal is to merge new changes into the existing knowledge while preserving its quality and completeness.

### Current Knowledge State

The existing .know/{domain}.md content (this is what you are updating):

{existing_know_file_content}

### Changes Since Last Analysis ({from_hash} -> {to_hash})

#### Commit Summary
{commit_log from ChangeManifest}

#### Files Changed
- New: {new_files list}
- Modified: {modified_files list}
- Deleted: {deleted_files list}
- Renamed: {renamed_files list}
- Delta: {delta_lines} lines changed (ratio {delta_ratio})

#### Detailed Diffs
{per-file unified diffs from git diff}

### Domain Criteria

{full_criteria_file_content}

### Experiential Knowledge (from .sos/land/)

**If a land file exists for this domain** (from pre-flight step 2.5 `land_files` map), inject:

The following synthesized knowledge was produced from cross-session experience.
When updating sections, integrate any relevant experiential observations that
were not present in the previous knowledge version. Verify factual claims
against the current codebase. Prefer codebase state for contradictions.

{land_file_content}

**If no land file exists for this domain**, omit this entire section. Do not inject an empty placeholder.

### Your Task

1. READ the existing knowledge document thoroughly
2. READ the change diffs to understand what changed
3. For each section in the knowledge document, determine:
   - Does this section need updating based on the changes? If no changes affect it, leave it UNCHANGED.
   - If changes affect it, READ the affected source files for full context (do not rely solely on diff text)
   - Produce the UPDATED section
4. Check for entirely NEW topics introduced by the changes that are not covered by existing sections
5. Check for sections that reference DELETED files/functions/types and correct them
6. Verify all file paths still exist using Glob/Read

### Output Format

Produce your output in TWO parts:

**Part 1: Knowledge Reference Body**

The COMPLETE updated knowledge document (same format as the original). Preserve all existing sections. Update only what changed. Add new sections where needed.

Start with the same top-level heading as the original document.

**IMPORTANT**: Always use FULL file paths from the project root. Abbreviated paths break automated validation.

**Part 2: Assessment Metadata**

After the knowledge body, on its own line produce a fenced metadata block:

```metadata
overall_grade: {A-F}
overall_percentage: {N.N}%
confidence: {0.0-1.0}
criteria_grades:
  {criterion_1_snake_case}: {grade}
  ...one entry per criterion from the criteria file...
sections_unchanged: [{list of unchanged section names}]
sections_updated: [{list of updated section names with brief reason}]
sections_added: [{list of new section names with brief reason}]
sections_corrected: [{list of sections with fixed broken refs}]
```

### Critical Rules
- DO NOT reduce knowledge quality. The updated document must be at least as comprehensive as the original.
- DO NOT hallucinate. If unsure whether a change affects a section, READ the source file.
- DO reference changes by examining the actual current source, not just the diff text.
- Preserve evidence quality: specific file paths, line numbers, function names.
- Your confidence should reflect how thoroughly you verified the updates against source.
")
```

## Phase 2b: Full Theoros Dispatch — Argus Pattern

Process the **full** queue. These domains either don't exist yet, have large deltas, hit their incremental cycle limit, or were force-regenerated.

> "One body, a hundred eyes, nothing unseen." — The Argus Pattern dispatches one theoros per domain in parallel.

**YOU MUST USE THE TASK TOOL TO DISPATCH THEOROS SUBAGENTS.** Do NOT attempt to observe the codebase yourself. Do NOT read source files and write .know/ files directly. Each domain MUST be delegated to a theoros subagent via `Task(subagent_type="theoros", ...)`. Theoros agents have dedicated context windows (150 turns each) for thorough codebase observation — performing observation in-context will exhaust your capacity and produce incomplete results.

**If `--all` (multiple domains)**: Launch ALL theoros agents in a SINGLE response block using multiple Task tool calls. This is the Argus Pattern — parallel dispatch, concurrent observation. Each theoros receives its own domain criteria and operates independently.

**If single domain**: Launch one theoros agent.

**CRITICAL**: When dispatching multiple domains, ALL Task calls MUST appear in the same response block to enable CC's parallel execution. Do NOT dispatch sequentially.

**CRITICAL**: Launch ALL theoros agents (both incremental Phase 2a and full Phase 2b) in the SAME response block. Do NOT dispatch Phase 2a first and wait, then dispatch Phase 2b. Combine them into a single parallel dispatch.

For each domain in the full generation queue, construct:

**If `--root` is set**: Add the following observation scope constraint to the theoros prompt (immediately after the domain criteria section):
```
### Observation Scope
Your observation is scoped to `{root}/` and its subtree. Only read files under this directory.
When you encounter references to code outside this scope, note them as external dependencies
rather than observing them directly.
```

```
Task(subagent_type="theoros", prompt="
## Knowledge Observation: {domain}

You are producing a KNOWLEDGE REFERENCE DOCUMENT, not an audit report.

Your domain criteria define WHAT to observe and document in the codebase. Instead of grading compliance against standards, assess the COMPLETENESS of your knowledge capture. The grading rubric measures how thoroughly you documented what exists, not whether what exists meets a standard.

### Reframing Your Audit Protocol

Your audit protocol still applies, but reframed:
- 'What to evaluate' -> 'What to observe and document'
- 'Evidence collection' -> 'Where to look and what to record'
- 'Assign letter grades' -> 'Assess completeness of knowledge capture'
- Grade A = comprehensive knowledge capture with evidence
- Grade F = incomplete or inaccurate knowledge capture

### Domain Criteria

{full_criteria_file_content}

### Experiential Knowledge (from .sos/land/)

**If a land file exists for this domain** (from pre-flight step 2.5 `land_files` map), inject:

The following synthesized knowledge was produced from cross-session experience.
Integrate relevant observations into the knowledge reference. Experiential
claims should be verified against the current codebase before inclusion.
Where experiential knowledge contradicts what you observe in code, note the
discrepancy and prefer the current codebase state.

Experiential insights about failure modes, design rationale, or operational
patterns should be integrated into relevant sections (e.g., "Boundaries and
Failure Modes", "Knowledge Gaps"). Attribute these as experiential observations
where the source is not directly verifiable from code.

{land_file_content}

**If no land file exists for this domain**, omit this entire section. Do not inject an empty placeholder.

### Output Format

Produce your output in TWO parts:

**Part 1: Knowledge Reference Body**

Structured markdown with one section per criterion. Each section documents what you observed in the codebase. Use specific file paths, type names, and package references. This becomes the body of the .know/ file.

Start with a top-level heading derived from the domain name:
# Codebase {Domain Title}

Then one H2 section per criterion from the criteria file, named EXACTLY as the criterion title appears (e.g., if the criterion is "Criterion 1: Package Structure", the section is "## Package Structure"). Follow the criteria order.

End with:
## Knowledge Gaps
(List anything you could not fully document and why.)

Be thorough. Include file paths, type names, function signatures, and import relationships. This document will be the primary reference for CC agents working in this codebase.

**IMPORTANT**: Always use FULL file paths from the project root (e.g., `internal/cmd/hook/budget.go`, NOT `cmd/hook/budget.go`). Abbreviated or package-relative paths break automated validation.

**Part 2: Assessment Metadata**

After the knowledge body, on its own line produce a fenced metadata block:

```metadata
overall_grade: {A-F}
overall_percentage: {N.N}%
confidence: {0.0-1.0}
criteria_grades:
  {criterion_1_snake_case}: {grade}
  {criterion_2_snake_case}: {grade}
  ...one entry per criterion from the criteria file...
```

The criteria_grades keys should be snake_case versions of the criterion names from the criteria file (e.g., "Package Structure" -> "package_structure", "Error Handling Style" -> "error_handling_style").

The confidence value is your self-assessment of how completely you covered the source scope. 1.0 = every file in scope examined. 0.5 = significant areas unexplored due to scope or turn limits.

### Scope Reminder

Read the **Scope** section in the domain criteria file above. It defines the target files and observation focus. Stay within the defined scope.
")
```

## Phase 3: Output Assembly

After ALL theoros agents return (wait for all parallel dispatches to complete):

For EACH domain's theoros output (both incremental and full), perform the following assembly:

1. **Parse theoros output**:
   - Extract the knowledge reference body (everything before the ` ```metadata` fence)
   - Extract the metadata block content (between the fences)
   - Parse confidence and grades from the metadata
   - If metadata block is missing or unparseable: use defaults (confidence: 0.5, grade: C)

2. **Construct the .know/ file**:
   Before assembling frontmatter, detect the project language by checking for manifest files in the scope root (`{root}/` when `--root` is set, otherwise project root):
   - If `go.mod` exists in scope root: set `source_scope` to `["./cmd/**/*.go", "./internal/**/*.go", "./go.mod"]`
   - Else if `package.json` exists in scope root: set `source_scope` to `["./src/**/*.ts", "./lib/**/*.ts", "./package.json"]`
   - Else if `pyproject.toml` exists in scope root: set `source_scope` to `["./src/**/*.py", "./app/**/*.py", "./pyproject.toml"]`
   - Else (no recognized manifest): set `source_scope` to `["./src/**/*"]`
   Note: `source_scope` globs are always written as relative to the `.know/` parent directory (using `./` prefix). The `ari knows` CLI normalizes them to repo-root-relative when computing staleness.

   **Determine update tracking fields** based on which queue the domain came from:

   - **Full queue**: `update_mode: "full"`, `incremental_cycle: 0`, `max_incremental_cycles: 3`
   - **Incremental queue**: `update_mode: "incremental"`, `incremental_cycle: {previous_cycle + 1}`, `max_incremental_cycles: 3`
     - Read the previous `incremental_cycle` from the existing .know/ file's frontmatter (default 0 if absent)

   Build YAML frontmatter:
   ```yaml
   ---
   domain: {domain}
   generated_at: "{current ISO 8601 UTC timestamp}"
   expires_after: "{expires_duration, default 7d}"
   source_scope:
     - "{first scope entry}"
     - "{second scope entry}"
     - "{third scope entry}"
   generator: theoros
   source_hash: "{git short SHA from pre-flight}"
   confidence: {confidence from theoros metadata}
   format_version: "1.0"
   update_mode: "{full or incremental}"
   incremental_cycle: {0 for full, previous+1 for incremental}
   max_incremental_cycles: 3
   land_sources:                              # ONLY if land file(s) were injected for this domain
     - ".sos/land/initiative-history.md"      # actual paths from LAND_MAP that existed (example)
   land_hash: "{sha256 hex from pre-flight step 2.5}"  # ONLY if land file(s) were injected
   ---
   ```
   If no land file was injected for this domain, omit `land_sources` and `land_hash` entirely (omitempty).
   The `land_hash` value comes from the SHA-256 computed during pre-flight step 2.5.
   The `land_sources` list contains the actual file paths from LAND_MAP that existed at generation time (not the domain name). For example, the `architecture` domain would list `.sos/land/initiative-history.md`, not `.sos/land/architecture.md`.
   Combine frontmatter + theoros knowledge body (Part 1 only, not the metadata fence).

3. **Read before write** (platform constraint):
   If the target file already exists (e.g., `--force` regeneration), you MUST read it before writing. The Write tool will fail otherwise.
   ```
   # Only needed if file exists and was not already read in this conversation
   Read("{knowDir}/{domain}.md")
   ```

4. **Write the file**:
   If `--root` is set:
   ```
   Write("{root}/.know/{domain}.md", frontmatter + body)
   ```
   Otherwise:
   ```
   Write(".know/{domain}.md", frontmatter + body)
   ```

5. **Verify the file**:
   ```
   Read("{knowDir}/{domain}.md", limit=20)
   ```
   Where `{knowDir}` is `{root}/.know` when `--root` is set, otherwise `.know`.
   Confirm frontmatter fields are present and valid. Confirm body sections exist.

## Phase 4: Report

**For single domain**, display:

```
## Knowledge Generated: .know/{domain}.md

| Field | Value |
|-------|-------|
| Domain | {domain} |
| Mode | {update_mode: full/incremental/time-only} |
| Source hash | {source_hash} |
| Confidence | {confidence} |
| Completeness | {grade} ({percentage}%) |
| Expires | {expiry_date} |
| Incremental cycle | {incremental_cycle} / {max_incremental_cycles} |

### Criteria Completeness
| Criterion | Grade |
|-----------|-------|
| {criterion_1_name} | {grade} |
| {criterion_2_name} | {grade} |
| ... | ... |

This file is consumable by any CC agent via `Read(".know/{domain}.md")`.
Regenerate with: `/know {domain} --force`
```

**For `--all` (Argus Pattern)**, display a combined report:

```
## Argus Pattern: {N} Domains Processed

| Domain | Mode | Grade | Confidence | Lines | Status |
|--------|------|-------|------------|-------|--------|
| {domain_1} | full | {grade} ({pct}%) | {confidence} | {line_count} | Generated |
| {domain_2} | incremental | {grade} ({pct}%) | {confidence} | {line_count} | Updated |
| {domain_3} | time-only | - | - | - | Refreshed |
| {skipped_domain} | - | - | - | - | Skipped (fresh) |

Source hash: {source_hash} | Expires: {expiry_date}

All files consumable via `Read(".know/{domain}.md")`.
Check freshness: `ari knows`
Check deltas: `ari knows --delta`
Regenerate all: `/know --all --force`
```

---

## Feature Knowledge Flow (`--scope=feature`)

This flow produces per-feature knowledge files in `.know/feat/`. It operates in two phases separated by a mandatory human review gate.

### Argument Variants

| Invocation | Behavior |
|------------|----------|
| `/know --scope=feature` | Full flow: census if needed, then generate all stale GENERATE features |
| `/know --scope=feature --census` | Census only: enumerate features and produce INDEX.md, then STOP |
| `/know --scope=feature --feature={slug}` | Single feature: skip census, generate one feature file directly |
| `/know --scope=feature --force` | Force regeneration: ignore freshness checks on all files |
| `/know --scope=feature --expires=DURATION` | Override default expiry (census: 30d, per-feature: 14d) |

### Feature Pre-flight

1. **Parse feature arguments**:
   - `--scope=feature`: Required. Activates the feature knowledge flow.
   - `--census`: Optional. If set, run census only and STOP after INDEX.md is produced.
   - `--feature={slug}`: Optional. If set, skip census entirely and generate a single feature.
   - `--force`: Optional. Skip freshness checks on census and feature files.
   - `--expires=DURATION`: Optional. Override default expiry per file type.

2. **Compute source_hash**:
   - Run: `git rev-parse --short HEAD`
   - Store result for frontmatter injection.

3. **Ensure directories exist**:
   - Run: `mkdir -p .know/feat`

4. **Seed freshness gate** (feature scope requires fresh codebase knowledge):
   - The 5 codebase `.know/` domains are formal prerequisites for feature analysis.
     They provide the structural map that feature criteria depend on.
   - Check if ALL 5 seed files exist: `.know/architecture.md`, `.know/scar-tissue.md`,
     `.know/conventions.md`, `.know/design-constraints.md`, `.know/test-coverage.md`
   - If ANY seed is missing: ERROR "Codebase knowledge seeds not found. Run `/know --all` first to generate base knowledge, then re-run `/know --scope=feature`."
   - If `--force` is set: skip freshness check, proceed with existing seeds.
   - Otherwise, read frontmatter of each seed (limit=20 lines per file) and check freshness:
     - Parse `generated_at` + `expires_after` for time-based staleness
     - Compare `source_hash` to current HEAD for code-based staleness
   - If ANY seed is stale, present the staleness report:
     ```
     ## Seed Freshness Check

     Feature analysis requires fresh codebase knowledge as context seeds.

     | Domain | Status | Reason |
     |--------|--------|--------|
     | {domain} | {FRESH/STALE} | {reason: time expired / code changed / fresh} |
     ...

     **Action required**: Run `/know --all` to refresh codebase domains, then re-run `/know --scope=feature`.
     ```
   - STOP. Do NOT proceed with stale seeds. The user must refresh and re-invoke.

5. **Load domain registry and criteria**:
   - Load pinakes skill: `Skill("pinakes")`
   - Read pinakes INDEX to find the Domain Registry table
   - Verify `feature-census` and `feature-knowledge` domains are registered with scope `feature`
   - If not found: ERROR "Feature domains not registered in pinakes. Run `ari sync` to materialize."
   - Read census criteria: `Read(".claude/skills/pinakes/domains/feature-census.md")`
   - Read feature knowledge criteria: `Read(".claude/skills/pinakes/domains/feature-knowledge.md")`
   - Store both for injection into theoros dispatch prompts.
   - Pre-load architecture seed for theoros injection: `Read(".know/architecture.md")`
   - Store architecture content for injection into theoros dispatch prompts.

6. **Route by argument**:
   - If `--feature={slug}`: Jump directly to [Feature Phase 2: Per-Feature Generation](#feature-phase-2-per-feature-generation) for the single slug.
   - If `--census`: Continue to Feature Phase 1 and STOP after it completes.
   - Otherwise: Continue to Feature Phase 1, then gate, then Feature Phase 2.

### Feature Phase 1: Census

**Purpose**: Enumerate all identifiable features in the project and produce `.know/feat/INDEX.md` with GENERATE/SKIP recommendations.

#### 1.1 Census Freshness Check

If `.know/feat/INDEX.md` exists AND `--force` is NOT set AND `--census` is NOT set:
- Read its YAML frontmatter, parse `generated_at` and `expires_after`
- Check git-diff staleness: compare `source_hash` to current HEAD
- If time-fresh AND code-fresh: report "Feature census is current (generated {date}, hash {hash}). Proceeding to feature generation." and skip to [Feature Human Gate](#feature-human-gate).

If `--census` IS set: always regenerate the census regardless of freshness (the user explicitly asked for a census re-run).

#### 1.2 Census Theoros Dispatch

**YOU MUST USE THE TASK TOOL.** Do NOT enumerate features yourself.

Dispatch a single theoros subagent with the census criteria:

```
Task(subagent_type="theoros", prompt="
## Feature Census Observation

You are producing a FEATURE CENSUS, not an audit report.

Your criteria define HOW to scan the project and enumerate its features. Instead of grading compliance, assess the COMPLETENESS of your enumeration. The grading rubric measures how many identifiable features you captured, not whether those features are well-implemented.

### Reframing Your Audit Protocol

Your audit protocol still applies, but reframed:
- 'What to evaluate' -> 'What features to discover and enumerate'
- 'Evidence collection' -> 'Which project sources to scan for feature signals'
- 'Assign letter grades' -> 'Assess completeness of feature enumeration'
- Grade A = every identifiable feature cataloged with evidence
- Grade F = fewer than half of identifiable features documented

### Census Criteria

{full_feature_census_criteria_content}

### Pre-loaded Context: Architecture Seed

The following is the project's architecture knowledge (.know/architecture.md). Use it as your
structural map to discover where features are implemented. Do NOT re-discover what this file
already documents -- use it to guide your source scanning.

{architecture_md_content}

Additional .know/ files available on demand via Read():
- .know/scar-tissue.md (past bugs, defensive patterns, failure catalog)
- .know/conventions.md (error handling, naming, file organization)
- .know/design-constraints.md (tensions, frozen areas, risk zones)
- .know/test-coverage.md (test gaps, coverage patterns)

### Output Format

Produce your output in TWO parts:

**Part 1: Feature Census Body**

Start with:
# Feature Census

Then produce a summary line:
> {N} features identified across {M} categories. {G} recommended for GENERATE, {S} recommended for SKIP.

Then produce ONE section per feature, ordered by category. Each feature section uses this EXACT format:

## {slug}

| Field | Value |
|-------|-------|
| Name | {human-readable name} |
| Category | {category} |
| Complexity | {HIGH / MEDIUM / LOW} |
| Recommendation | **{GENERATE / SKIP}** |
| Confidence | {0.0-1.0} |

**Source Evidence**:
- {source_file_1}: {what it reveals about this feature}
- {source_file_2}: {what it reveals about this feature}

**Rationale**: {one-paragraph justification for GENERATE or SKIP, citing triage heuristics}

---

End with:
## Census Gaps
(List any areas of the project that were difficult to classify or where feature boundaries were ambiguous.)

**IMPORTANT**: Use kebab-case slugs. Every feature must have all 7 fields. Use the triage heuristics from the criteria to justify GENERATE vs SKIP.

**Part 2: Assessment Metadata**

After the census body, on its own line produce a fenced metadata block:

```metadata
overall_grade: {A-F}
overall_percentage: {N.N}%
confidence: {0.0-1.0}
criteria_grades:
  source_coverage: {grade}
  feature_enumeration: {grade}
  classification_quality: {grade}
  output_format_compliance: {grade}
```

### Scope Reminder

Read the **Scope** section in the census criteria above. It defines the target sources to scan. Scan ALL of them.
")
```

#### 1.3 Census Output Assembly

After the census theoros returns:

1. **Parse theoros output**:
   - Extract the census body (everything before the ` ```metadata` fence)
   - Extract the metadata block content
   - Parse confidence and grades from the metadata
   - If metadata block is missing or unparseable: use defaults (confidence: 0.5, grade: C)

2. **Construct `.know/feat/INDEX.md`**:
   ```yaml
   ---
   domain: feat/index
   generated_at: "{current ISO 8601 UTC timestamp}"
   expires_after: "{expires_duration, default 30d}"
   source_scope:
     - "./rites/*/manifest.yaml"
     - "./internal/*/"
     - "./docs/decisions/ADR-*.md"
     - "./.claude/commands/*.md"
     - "./.claude/agents/*.md"
     - "./INTERVIEW_SYNTHESIS.md"
     - "./.know/*.md"
   generator: theoros
   source_hash: "{git short SHA}"
   confidence: {confidence from metadata}
   format_version: "1.0"
   ---
   ```
   Combine frontmatter + census body (Part 1 only).

3. **Read before write** (platform constraint):
   If `.know/feat/INDEX.md` already exists, you MUST read it before writing. The Write tool will fail otherwise.
   ```
   # Only needed if file exists and was not already read in this conversation
   Read(".know/feat/INDEX.md")
   ```

4. **Write the file**:
   ```
   Write(".know/feat/INDEX.md", frontmatter + body)
   ```

5. **Verify the file**:
   ```
   Read(".know/feat/INDEX.md", limit=30)
   ```
   Confirm frontmatter is valid. Confirm feature sections exist with structured entries.

6. **Report census result**:
   ```
   ## Feature Census Complete: .know/feat/INDEX.md

   | Field | Value |
   |-------|-------|
   | Features found | {total_count} |
   | GENERATE | {generate_count} |
   | SKIP | {skip_count} |
   | Source hash | {source_hash} |
   | Confidence | {confidence} |
   | Completeness | {grade} ({percentage}%) |
   | Expires | {expiry_date} |
   ```

7. **If `--census` flag was set**: STOP here. Report is complete.

### Feature Human Gate

**THIS GATE IS MANDATORY.** Do NOT proceed to Phase 2 automatically.

Present the census results to the user and ask for explicit approval:

```
The feature census has been written to `.know/feat/INDEX.md`.

**Action required**: Review the census before feature generation begins.

Read the file with: `Read(".know/feat/INDEX.md")`

Check:
1. Are the feature boundaries correct? (Are separate features incorrectly merged, or one feature incorrectly split?)
2. Are the GENERATE/SKIP recommendations appropriate? (Should any SKIP become GENERATE, or vice versa?)
3. Are there missing features not captured by the census?

You may edit `.know/feat/INDEX.md` directly to adjust recommendations before proceeding.

**When ready**: Reply with "proceed" (or "proceed with changes") to begin per-feature knowledge generation for all GENERATE features.
```

**Wait for user response.** Do NOT continue until the user explicitly confirms. If the user edits the INDEX and says "proceed with changes", re-read INDEX.md before continuing.

### Feature Phase 2: Per-Feature Generation

**Purpose**: Generate `.know/feat/{slug}.md` for each GENERATE feature in the census.

#### 2.1 Build Feature Generation Queue

**If invoked via `--feature={slug}`** (single feature mode):
- The slug is the only item in the queue.
- Read `.know/feat/INDEX.md` to extract the census entry for this slug.
- If INDEX.md does not exist: ERROR "Feature census not found. Run `/know --scope=feature --census` first to enumerate features."
- If slug not found in INDEX.md: ERROR "Feature '{slug}' not found in census. Available features: {list of slugs from INDEX.md}"

**If invoked via full flow** (after human gate):
- Re-read `.know/feat/INDEX.md` (user may have edited it).
- Parse every feature section. Extract slug and recommendation for each.
- For each feature with recommendation **GENERATE**:
  - If `.know/feat/{slug}.md` exists AND `--force` not set:
    - Read its YAML frontmatter, parse `generated_at` and `expires_after`
    - Check git-diff staleness: compare `source_hash` to current HEAD
    - If time-fresh AND code-fresh: SKIP (report "Feature '{slug}' is current")
  - Otherwise: ADD to generation queue
- If generation queue is empty: report "All GENERATE features are current. Use --force to regenerate." and STOP.
- Report: "Generating {N} feature(s): {slug_list}"

#### 2.2 Extract Census Context per Feature

For each slug in the generation queue, extract from `.know/feat/INDEX.md`:
- The full feature section (slug, name, category, source_evidence, complexity, recommendation rationale)
- Store as `census_context` for injection into the per-feature theoros prompt.

#### 2.3 Per-Feature Theoros Dispatch -- Argus Pattern

**YOU MUST USE THE TASK TOOL.** Do NOT write feature knowledge yourself.

**If multiple features**: Launch ALL theoros agents in a SINGLE response block. This is the Argus Pattern — parallel dispatch, concurrent observation.

**If single feature** (via `--feature={slug}`): Launch one theoros agent.

**CRITICAL**: When dispatching multiple features, ALL Task calls MUST appear in the same response block to enable CC's parallel execution. Do NOT dispatch sequentially.

For each feature slug in the generation queue, construct:

```
Task(subagent_type="theoros", prompt="
## Feature Knowledge Observation: {slug}

You are producing a FEATURE KNOWLEDGE REFERENCE for the feature '{name}', not an audit report.

Your criteria define the four dimensions of feature knowledge to capture. Instead of grading compliance, assess the COMPLETENESS of your knowledge documentation. The grading rubric measures how thoroughly you documented the feature, not whether the feature is well-implemented.

### Reframing Your Audit Protocol

Your audit protocol still applies, but reframed:
- 'What to evaluate' -> 'What to observe and document about this feature'
- 'Evidence collection' -> 'Where to look and what to record'
- 'Assign letter grades' -> 'Assess completeness of feature knowledge capture'
- Grade A = an agent reading only this file could modify the feature safely
- Grade F = the document is too incomplete for safe modification

### Census Context for This Feature

The project-wide feature census identified this feature with the following classification:

{census_context_for_this_slug}

Use the source evidence listed above as your STARTING POINT for investigation. Expand beyond these sources as needed to build complete knowledge.

### Feature Knowledge Criteria

{full_feature_knowledge_criteria_content}

### Pre-loaded Context: Architecture Seed

The following is the project's architecture knowledge (.know/architecture.md). Use it as your
structural map to locate this feature's implementation. Do NOT re-discover what this file
already documents.

{architecture_md_content}

Additional .know/ files available on demand via Read():
- .know/scar-tissue.md (past bugs, defensive patterns -- valuable for Boundaries section)
- .know/conventions.md (error handling, naming -- valuable for understanding code patterns)
- .know/design-constraints.md (tensions, frozen areas -- valuable for Boundaries section)
- .know/test-coverage.md (test gaps -- valuable for Implementation Map section)

### Output Format

Produce your output in TWO parts:

**Part 1: Feature Knowledge Body**

Start with:
# {feature_name}

Then produce the four knowledge dimensions as H2 sections, in this exact order:

## Purpose and Design Rationale
(Why this feature exists, what problem it solves, ADRs, rejected alternatives, tradeoffs)

## Conceptual Model
(Key abstractions, terminology, state machines/lifecycles, inter-feature relationships)

## Implementation Map
(Packages, key types, entry points, data flow, public API surface, test locations)

## Boundaries and Failure Modes
(Scope limitations, edge cases, error paths, interaction points, configuration boundaries)

End with:
## Knowledge Gaps
(List anything you could not fully document and why.)

Be thorough. Include file paths, type names, function signatures, and import relationships. This document will be the primary reference for CC agents working on this feature.

**IMPORTANT**: Always use FULL file paths from the project root (e.g., `internal/cmd/hook/budget.go`, NOT `cmd/hook/budget.go`). Abbreviated or package-relative paths break automated validation.

**Part 2: Assessment Metadata**

After the knowledge body, on its own line produce a fenced metadata block:

```metadata
overall_grade: {A-F}
overall_percentage: {N.N}%
confidence: {0.0-1.0}
criteria_grades:
  purpose_and_design_rationale: {grade}
  conceptual_model: {grade}
  implementation_map: {grade}
  boundaries_and_failure_modes: {grade}
```

### Scope Reminder

Focus on the packages and files relevant to '{slug}'. Use the source_evidence from the census context as your starting point. Consult existing `.know/architecture.md` and `.know/scar-tissue.md` for structural context and failure history.
")
```

#### 2.4 Per-Feature Output Assembly

After ALL per-feature theoros agents return (wait for all parallel dispatches to complete):

For EACH feature's theoros output, perform the following assembly:

1. **Parse theoros output**:
   - Extract the feature knowledge body (everything before the ` ```metadata` fence)
   - Extract the metadata block content
   - Parse confidence and grades from the metadata
   - If metadata block is missing or unparseable: use defaults (confidence: 0.5, grade: C)

2. **Determine source_scope for this feature**:
   From the census context for this slug, extract the `source_evidence` entries. Convert them to glob patterns for the frontmatter. Adapt to the detected project language:
   - Source directories: use language-appropriate glob (e.g., `"./internal/materialize/**/*.go"` for Go, `"./src/auth/**/*.ts"` for TypeScript)
   - Decision records: use the path as-is (e.g., `"./docs/decisions/ADR-0026*.md"`)
   - Documentation: use the path as-is (e.g., `"./docs/feature-name.md"`)
   - Always include `"./.know/architecture.md"` (structural context baseline)

3. **Construct `.know/feat/{slug}.md`**:
   ```yaml
   ---
   domain: feat/{slug}
   generated_at: "{current ISO 8601 UTC timestamp}"
   expires_after: "{expires_duration, default 14d}"
   source_scope:
     - "{derived from census source_evidence}"
     - "./.know/architecture.md"
   generator: theoros
   source_hash: "{git short SHA from pre-flight}"
   confidence: {confidence from metadata}
   format_version: "1.0"
   ---
   ```
   Combine frontmatter + feature knowledge body (Part 1 only).

4. **Read before write** (platform constraint):
   If `.know/feat/{slug}.md` already exists, you MUST read it before writing. The Write tool will fail otherwise.
   ```
   # Only needed if file exists and was not already read in this conversation
   Read(".know/feat/{slug}.md")
   ```

5. **Write the file**:
   ```
   Write(".know/feat/{slug}.md", frontmatter + body)
   ```

6. **Verify the file**:
   ```
   Read(".know/feat/{slug}.md", limit=20)
   ```
   Confirm frontmatter fields are present and valid. Confirm all four knowledge dimension sections exist.

### Feature Phase 3: Report

**For single feature** (via `--feature={slug}`), display:

```
## Feature Knowledge Generated: .know/feat/{slug}.md

| Field | Value |
|-------|-------|
| Feature | {name} ({slug}) |
| Category | {category} |
| Source hash | {source_hash} |
| Confidence | {confidence} |
| Completeness | {grade} ({percentage}%) |
| Expires | {expiry_date} |

### Knowledge Dimensions
| Dimension | Grade |
|-----------|-------|
| Purpose and Design Rationale | {grade} |
| Conceptual Model | {grade} |
| Implementation Map | {grade} |
| Boundaries and Failure Modes | {grade} |

This file is consumable by any CC agent via `Read(".know/feat/{slug}.md")`.
Regenerate with: `/know --scope=feature --feature={slug} --force`
```

**For full flow or multi-feature** (Argus Pattern), display a combined report:

```
## Feature Knowledge: {N} Features Generated

| Feature | Category | Grade | Confidence | Lines | Status |
|---------|----------|-------|------------|-------|--------|
| {slug_1} | {category} | {grade} ({pct}%) | {confidence} | {line_count} | Generated |
| {slug_2} | {category} | {grade} ({pct}%) | {confidence} | {line_count} | Generated |
| ... | ... | ... | ... | ... | ... |
| {skipped_slug} | {category} | - | - | - | Skipped (fresh) |
| {skip_slug} | {category} | - | - | - | Skipped (SKIP in census) |

Source hash: {source_hash}

All files consumable via `Read(".know/feat/{slug}.md")`.
Census: `Read(".know/feat/INDEX.md")`
Re-census: `/know --scope=feature --census`
Regenerate all: `/know --scope=feature --force`
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Domain not in pinakes | ERROR with available codebase domains |
| Theoros dispatch fails | ERROR "Knowledge generation failed: {reason}" |
| Theoros output unparseable | Write body as-is with default metadata, WARN about metadata parsing failure |
| .know/ directory not writable | ERROR with permission details |
| Git not available (no source_hash) | Use "unknown" as source_hash, WARN |
| `--scope=feature --feature={slug}` but no INDEX.md | ERROR "Feature census not found. Run `/know --scope=feature --census` first." |
| `--scope=feature --feature={slug}` but slug not in INDEX | ERROR "Feature '{slug}' not in census. Available: {list}" |
| Census theoros returns unparseable feature entries | WARN about format issues, write census as-is, let human gate catch errors |
| `--scope=feature` with `--all` | ERROR "Cannot combine --scope=feature with --all. Use --scope=feature alone for full feature flow." |
| `--scope=feature` with positional domain arg | ERROR "Cannot combine --scope=feature with a domain argument. Feature scope generates feature knowledge, not domain knowledge." |

## Anti-Patterns

- **Performing observation yourself instead of dispatching theoros**: You are the ORCHESTRATOR, not the observer. Your job is to load criteria, dispatch theoros subagents via Task tool, then assemble their output into .know/ files. If you find yourself reading source code and writing knowledge sections, STOP — you are violating the dispatch pattern. Each theoros gets its own 150-turn context window, which is why parallel dispatch produces better results than in-context observation.
- **Modifying theoros agent prompt**: The reframing happens in THIS dispatch prompt, not in the agent definition. Theoros remains a general-purpose domain auditor.
- **Skipping verification**: Always Read the .know/ file after writing to confirm correctness.
- **Ignoring expiry**: Respect the expiry mechanism. Regenerating current knowledge wastes theoros capacity.
- **Hardcoding architecture-only**: This dromenon accepts any codebase-scoped domain. Architecture is the default, but the mechanism is generic.
- **Skipping the human gate in feature flow**: The census-to-generation gate is MANDATORY. Do NOT proceed to per-feature generation without explicit user confirmation. The census may contain incorrect feature boundaries that the user must review.
- **Generating features marked SKIP**: Only features with GENERATE recommendation enter the generation queue. SKIP features are excluded unless the user edits INDEX.md to change the recommendation before confirming.
- **Sequential feature dispatch**: When generating multiple features, ALL Task calls MUST be in one response block (Argus Pattern). Sequential dispatch wastes wall-clock time.
