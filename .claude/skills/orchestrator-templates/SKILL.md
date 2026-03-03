---
name: orchestrator-templates
description: "Shared schemas for orchestrator consultation patterns. Use when: consulting an orchestrator about next steps, structuring phase transition requests, formatting consultation responses. Triggers: orchestrator consultation, consultation request, consultation response, phase transition schema."
invokable: skill
---

# Orchestrator Templates

> Structured schemas for orchestrator consultation requests and responses.

## Purpose

This skill provides the canonical YAML schemas used by orchestrator agents when they are consulted by the main agent. These schemas ensure consistent, structured communication for multi-phase workflow coordination.

## Schemas

### Consultation Request Schema
[consultation-request.md](schemas/consultation-request.md) - Structure for consulting an orchestrator

**When to use**: Main agent needs to consult orchestrator about next steps, phase transitions, or specialist routing.

### Consultation Response Schema
[consultation-response.md](schemas/consultation-response.md) - Structure for orchestrator's directive response

**When to use**: Orchestrator returns structured guidance to main agent.

## Usage Pattern

```
Main Agent → CONSULTATION_REQUEST → Orchestrator → CONSULTATION_RESPONSE → Main Agent
```

The orchestrator is a stateless advisor. It receives structured context and returns structured directives. The main agent controls all execution.

## Related Skills

- `10x-workflow` skill — Agent coordination patterns
- `prompting` skill — Agent invocation guidance
