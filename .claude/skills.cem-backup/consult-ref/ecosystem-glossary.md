# Ecosystem Glossary

> Terms and definitions for the Claude Code ecosystem

## Core Concepts

### Agent
A specialized AI persona with defined responsibilities, tools, and outputs. Agents are the workers in the system.

### Team Pack
A collection of agents organized around a domain (e.g., 10x-dev-pack for development). Switching teams changes which agents are available.

### Workflow
The sequence of phases work progresses through. All workflows are sequential with handoffs between phases.

### Phase
A stage in a workflow, typically handled by one agent. Phases produce artifacts and have handoff criteria.

### Artifact
A document produced during a workflow (PRD, TDD, ADR, code, test report, etc.).

### Command
A slash command that triggers an action (`/start`, `/task`, `/consult`, etc.).

### Skill
A knowledge module that provides domain expertise on-demand. Skills are referenced but not invoked directly.

### Session
A unit of work with its own context. Sessions can be started, parked, continued, and wrapped.

### Playbook
A documented sequence of commands for accomplishing a specific goal.

---

## Commands

### /consult
The meta-navigation command. Provides ecosystem guidance, team recommendations, and playbooks.

### /start
Initializes a new work session with context capture.

### /task
Executes a single task through full workflow lifecycle.

### /sprint
Coordinates multiple tasks as a sprint.

### /hotfix
Fast-track workflow for urgent bug fixes.

### /spike
Time-boxed research with no production code.

### /architect
Design phase only, produces TDD and ADRs.

### /build
Implementation phase only, assumes design exists.

### /qa
Validation phase only, runs QA adversary.

### /park
Pauses session and preserves state.

### /continue
Resumes a parked session.

### /wrap
Finalizes session with quality gates.

### /handoff
Transfers work between agents.

### /pr
Creates a pull request.

### /code-review
Structured code review.

### /team
Switches team pack or lists available.

---

## Artifacts

### PRD (Product Requirements Document)
Defines what to build and why. Produced by Requirements Analyst.

### TDD (Technical Design Document)
Defines how to build it. Produced by Architect.

### ADR (Architecture Decision Record)
Documents a significant technical decision. Produced by Architect.

### SESSION_CONTEXT.md
Tracks current session state, artifacts, and blockers.

---

## Teams

### 10x-dev-pack
Full-cycle development: requirements → design → implementation → validation.

### doc-team-pack
Documentation: scoping → drafting → editing → publishing.

### hygiene-pack
Code quality: assessment → detection → remediation → validation.

### debt-triage-pack
Technical debt: discovery → prioritization → planning.

### sre-pack
Operations: response → analysis → remediation → planning.

### security-pack
Security: threat-modeling → compliance → testing → review.

### intelligence-pack
Analytics: instrumentation → research → experimentation → synthesis.

### rnd-pack
R&D: scouting → integration → prototyping → future-architecture.

### strategy-pack
Strategy: market-research → competitive-analysis → business-modeling → planning.

---

## Complexity Levels

### SCRIPT / SPOT / PAGE / QUICK / TASK / PATCH / METRIC / SPIKE / TACTICAL
Lowest complexity. Single file, minimal scope.

### MODULE / SECTION / PROJECT / FEATURE / EVALUATION / STRATEGIC
Medium complexity. Component or feature scope.

### SERVICE / SITE / SYSTEM / INITIATIVE / MOONSHOT / TRANSFORMATION
High complexity. Service or system scope.

### PLATFORM / CODEBASE / AUDIT
Highest complexity. Entire system scope.

---

## Infrastructure

### Hooks
Scripts that run automatically on events (SessionStart, Stop, PreToolUse, PostToolUse).

### Global Agents
Agents that persist across team swaps (Consultant).

### TTY-Based Session Isolation
Each terminal gets its own session context.

### Roster
The external repository containing team packs (`~/Code/roster/`).

### swap-team.sh
Script that swaps agent files when changing teams.

---

## Models

### opus (claude-opus-4-5)
Used for complex reasoning, design, analysis, review.

### sonnet
Used for execution, implementation, fast iteration.

---

## States

### ACTIVE
Session is in progress.

### PARKED
Session is paused, state preserved.

### COMPLETED
Session has been wrapped and finalized.

---

## Patterns

### Sequential Workflow
Work progresses through phases in order. All teams use this pattern.

### Complexity Gating
Higher complexity levels include more phases.

### Handoff Criteria
Explicit requirements that must be met before phase transition.

### Quality Gates
Validation checks run before session completion.
