---
name: rite-discovery
description: "Dynamic rite metadata from knossos. Use when: listing available rites, checking rite capabilities, looking up agent counts or domains for a rite. Triggers: list rites, rite capabilities, what rites exist, rite metadata."
---

# Rite Discovery

> Provides structured rite metadata by reading from `rites/*/orchestrator.yaml`.

## Purpose

Enables dynamic rite discovery without hardcoding rite counts or capabilities. Other skills (`consult-ref`, `rite-ref`) reference this skill for current rite catalog.

## Usage

This skill provides read-only rite metadata. It does not switch rites.

### List All Rites

Read all orchestrator.yaml files from `$KNOSSOS_HOME/rites/*/orchestrator.yaml` and extract:
- Rite name, domain, description
- Quick-switch command
- Agent catalog (from rites/{name}/agents/*.md)
- Routing conditions (what triggers each specialist)

### Match Intent to Rite

Given a user query, compare against rite routing conditions:
1. Parse query for key verbs (build, fix, deploy, document, etc.)
2. Match against rite domains and routing conditions
3. Return ranked list with confidence scores

## Data Source

**Primary**: `$KNOSSOS_HOME/rites/*/orchestrator.yaml`
**Supplementary**: `$KNOSSOS_HOME/rites/*/README.md` for use cases

### Current Rite Inventory

| Rite | Command | Domain | Workflow | Agents |
|------|---------|--------|----------|--------|
| 10x-dev | /10x | Software development | requirements → design → implementation → validation | 4 |
| arch | /arch | Architecture analysis | discovery → synthesis → evaluation → remediation | 4 |
| debt-triage | /debt | Technical debt management | collection → assessment → planning | 3 |
| docs | /docs | Documentation lifecycle | audit → architecture → writing → review | 4 |
| ecosystem | /ecosystem | Ecosystem infrastructure | analysis → design → implementation → documentation → validation | 5 |
| forge | /forge | Agent rite creation | discovery → architecture → implementation → validation → publishing → catalog | 6 |
| hygiene | /hygiene | Code quality | assessment → planning → execution → audit | 4 |
| intelligence | /intelligence | Product analytics | discovery → analysis → experimentation → measurement | 4 |
| rnd | /rnd | Technology exploration | question → exploration → synthesis → recommendation | 4 |
| security | /security | Security assessment | discovery → analysis → hardening → verification | 4 |
| sre | /sre | Site reliability | discovery → analysis → implementation → verification | 4 |
| strategy | /strategy | Business strategy | market-research → competitive-analysis → business-modeling → strategic-planning | 4 |

**Total**: 12 rites, 50 agents

Note: `shared` is a dependency bundle, not a user-facing rite.
To refresh this table, run `ari sync` which reads from `rites/*/orchestrator.yaml`.

## Schema Reference

See [schemas/rite-profile.yaml](schemas/rite-profile.yaml) for the structured output format.

## Integration Points

- **consult-ref**: Calls rite-discovery for routing recommendations
- **rite-ref**: Calls rite-discovery for --list output
- **SessionStart hook**: May call rite-discovery for context injection
