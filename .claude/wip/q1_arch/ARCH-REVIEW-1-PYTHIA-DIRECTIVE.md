# Architectural Review 1: Pythia Coordination Directive

**Date**: 2026-02-18
**Scope**: Pythia's orchestration decisions for the architectural review swarm
**Methodology**: CONSULTATION_RESPONSE format documenting the parallel dispatch directive
**Review ID**: ARCH-REVIEW-1

---

## 1. CONSULTATION_RESPONSE: Parallel Dispatch Directive

When consulted for the architectural review, Pythia returned a parallel dispatch directive for 8 specialist agents (6 analysis agents in 3 steel-man/straw-man pairs, plus 2 synthesis agents).

### The Directive

```yaml
CONSULTATION_RESPONSE:
  directive: parallel_dispatch
  rationale: >
    The exploration phase produced comprehensive codebase mapping from 10 agents.
    The architectural review phase requires simultaneous analysis from multiple
    perspectives to prevent anchoring bias. Steel-man and straw-man pairs for
    each analysis dimension ensure balanced assessment.

  specialist_dispatch:
    # Pair 1: Topology
    - agent: topology-cartographer
      variant: steel-man
      prompt: "Defend the architecture. For each subsystem, argue why the design
        decisions are proportionate to the problem. Focus on: descriptor system,
        5-tier detection, caching philosophy, SaveSession UoW, HolderFactory,
        query engine, dual-mode deployment."

    - agent: topology-cartographer
      variant: straw-man
      prompt: "Critique the architecture. For each subsystem, argue why the design
        is over-complex, inconsistent, or fragile. Focus on: triple registry,
        cache invalidation gap, hardcoded sections, import side-effects,
        freshness complexity, frozen escape hatches, singleton constellation."

    # Pair 2: Dependencies
    - agent: dependency-analyst
      variant: steel-man
      prompt: "Defend the coupling topology. For each major integration point,
        argue why the coupling level is intentional and appropriate. Analyze
        fan-in gravity wells, protocol boundaries, cohesion."

    - agent: dependency-analyst
      variant: straw-man
      prompt: "Critique the coupling topology. For each major integration point,
        argue why the coupling is excessive, leaky, or fragile. Analyze
        abstraction leaks, circular dependencies, configuration coupling."

    # Pair 3: Structure
    - agent: structure-evaluator
      variant: steel-man
      prompt: "Defend boundary alignment. For each package, argue that boundaries
        align with domain concepts. Analyze detection/, entity_registry,
        descriptors.py, query/ as well-aligned examples."

    - agent: structure-evaluator
      variant: straw-man
      prompt: "Critique boundary alignment. For each package, identify where
        boundaries diverge from domain. Analyze models/business/ (8 sub-domains),
        services/ (mixed concerns), persistence/ (god object). Identify
        anti-patterns: parallel hierarchy, shotgun surgery, feature envy."

    # Synthesis
    - agent: remediation-planner
      variant: steel-straw-synthesis
      prompt: "Synthesize steel-man and straw-man findings into: opportunities
        (5+), gaps (7+), trajectory assessment, bus factor signals, and
        architectural paradoxes. Produce essential-vs-accidental complexity
        verdicts."

    - agent: remediation-planner
      variant: philosophy-extraction
      prompt: "Extract the architectural philosophy from the codebase's
        consistent trade-offs. Analyze: what it values most, the defensive
        onion metaphor, philosophy contradictions, consistency model,
        complexity budget, failure modes, cognitive load."

  state_update:
    current_phase: architectural_review
    artifacts_in_progress:
      - topology-steel-man
      - topology-straw-man
      - dependency-steel-man
      - dependency-straw-man
      - structure-steel-man
      - structure-straw-man
      - opportunity-gap-synthesis
      - philosophy-extraction
    output_directory: ".claude/wip/q1_arch/"
    next_phases:
      - synthesis: "Main agent synthesizes all 8 specialist outputs"
      - persistence: "Context Engineer writes canonical documents"

  throughline:
    rationale: >
      Sequential analysis (topology -> dependency -> structure -> remediation)
      would allow each phase to anchor the next. Parallel dispatch prevents
      anchoring: each specialist works from the same exploration data without
      seeing other specialists' conclusions.

      The steel-man/straw-man pairing forces balanced assessment. A single
      analyst would produce biased findings (either too generous or too
      critical). Dual perspectives ensure the synthesis captures both
      strengths and weaknesses accurately.

    decisions_made:
      - Bypassed sequential pipeline in favor of parallel dispatch
      - Created 3 steel-man/straw-man pairs instead of 3 sequential phases
      - Added philosophy extraction as separate specialist (not part of remediation)
      - Specified parallel execution to prevent anchoring between specialists

    open_questions:
      - Whether the 10-agent exploration data is sufficient for all analysis dimensions
      - Whether specialist prompts are specific enough for focused analysis
      - Whether synthesis can reconcile conflicting steel-man/straw-man findings
```

---

## 2. Specialist Variant Prompts

### Topology Steel-Man Prompt

```
You are the steel-man topology analyst. Your task is to provide the strongest
possible defense of this architecture's design decisions.

EXPLORATION DATA: [10-agent exploration findings]

FOR EACH SUBSYSTEM:
1. Identify the problem the design addresses
2. Explain why the chosen approach is proportionate to the problem
3. Compare with simpler alternatives and explain why they would be insufficient
4. Identify where complexity is genuinely earned

SUBSYSTEMS TO DEFEND:
- Descriptor system (ADR-0081) -- ~800 lines boilerplate eliminated
- 5-tier entity detection -- 17 types, calibrated confidence
- Caching philosophy -- operational resilience, 4:2 servable ratio
- extra="ignore" -- forward compatibility for third-party API
- SaveSession UoW -- phase-based commit over non-transactional API
- Dual-mode deployment -- single Docker image, env-driven dispatch
- HolderFactory -- 9 holders from ~70 to 3-5 lines each
- Query engine -- algebraic predicate AST, stateless compiler

OUTPUT: Structured defense per subsystem with proportionality verdicts.
```

### Topology Straw-Man Prompt

```
You are the straw-man topology analyst. Your task is to provide the strongest
possible critique of this architecture's design weaknesses.

EXPLORATION DATA: [10-agent exploration findings]

FOR EACH WEAKNESS:
1. Describe the current state precisely (file paths, line numbers, metrics)
2. Explain why this is problematic (not just "could be better")
3. Quantify the impact where possible (lines, concepts, coupling score)
4. Identify the root cause (not just symptoms)

WEAKNESSES TO EXAMINE:
- Triple registry problem (3 overlapping registries, no cross-validation)
- Cache invalidation gap (external mutations invisible)
- 47 hardcoded section names (3 parallel representations)
- Import-time side effects (register_all_models, __getattr__, lazy imports)
- 31 distinct caching concepts (7 freshness types, 2 systems, 2 coalescers)
- Philosophy contradiction (freshness first-class vs best-effort invalidation)
- Pydantic frozen escape hatches (object.__setattr__, extra="allow")
- Singleton constellation (6+ singletons, no coordinator)
- Async/sync duality (88 sync bridges, 14 threading.Lock)

OUTPUT: Structured critique per weakness with severity assessment.
```

### Dependency Steel-Man Prompt

```
You are the steel-man dependency analyst. Your task is to defend the coupling
topology as intentional and appropriate.

EXPLORATION DATA: [10-agent exploration findings]

ANALYSIS FRAMEWORK:
1. Fan-in gravity wells: Identify why high fan-in modules are correctly positioned
2. Protocol boundaries: Evaluate where CacheProvider, AuthProvider etc. provide clean DI
3. Cohesion: Assess whether package boundaries reflect domain cohesion
4. Integration patterns: Classify each major integration as intentional coupling

OUTPUT: Integration pattern classification table with coupling justification.
```

### Dependency Straw-Man Prompt

```
You are the straw-man dependency analyst. Your task is to identify problematic
coupling, leaks, and fragility in the dependency topology.

EXPLORATION DATA: [10-agent exploration findings]

ANALYSIS FRAMEWORK:
1. Abstraction leaks: Find where internal details cross package boundaries
2. Circular dependencies: Map lazy-import-managed cycles and assess fragility
3. Configuration coupling: Analyze centralized definition vs scattered consumption
4. Platform dependency: Assess coupling to 7 autom8y-* packages

OUTPUT: Coupling hotspot table with scores and abstraction leak inventory.
```

### Structure Steel-Man Prompt

```
You are the steel-man structure evaluator. Your task is to demonstrate where
package boundaries align with domain concepts.

EXPLORATION DATA: [10-agent exploration findings]

WELL-ALIGNED EXAMPLES:
- detection/ -- clean domain boundary, single responsibility per tier
- core/entity_registry.py -- SSoT with clean API
- descriptors.py -- declarative pattern with clear scope
- query/ -- algebraic engine with clean decomposition

For each, assess: single responsibility, internal cohesion, external coupling,
API surface, testability.

OUTPUT: Boundary alignment table with per-package assessment.
```

### Structure Straw-Man Prompt

```
You are the straw-man structure evaluator. Your task is to identify where
package boundaries diverge from domain concepts and anti-patterns exist.

EXPLORATION DATA: [10-agent exploration findings]

DIVERGENCE EXAMPLES:
- models/business/ -- 8 sub-domains, 85 exports
- services/ -- mixed concerns (resolver, strategy, query, discovery)
- persistence/ -- SaveSession dominates (1,853 lines)

ANTI-PATTERNS TO IDENTIFY:
- Parallel hierarchy (automation/ vs lifecycle/)
- Shotgun surgery (new entity type requires 4-7 file changes)
- Feature envy (cross-package private imports)
- God module (DataServiceClient, SaveSession)

OUTPUT: Anti-pattern inventory with essential-vs-accidental complexity verdicts.
```

### Remediation Steel-Straw Synthesis Prompt

```
You are the remediation synthesizer. Reconcile steel-man and straw-man findings
into actionable assessment.

INPUT: Steel-man and straw-man outputs from topology, dependency, and structure pairs.

PRODUCE:
1. State assessment (maturity phase, essential-to-accidental ratio)
2. Five opportunities (exploitable strengths and unexploited foundations)
3. Seven gaps (missing capabilities, undocumented behaviors, safety issues)
4. Trajectory assessment (direction, alignment, divergence risks)
5. Bus factor signals (concentrated knowledge areas)
6. Five architectural paradoxes (contradictions that reveal design tensions)

OUTPUT: Structured synthesis with severity/likelihood/leverage ratings.
```

### Philosophy Extraction Prompt

```
You are the philosophy extractor. Identify the underlying architectural
philosophy from the codebase's consistent trade-offs.

INPUT: All exploration data + steel-man/straw-man outputs.

PRODUCE:
1. What the codebase values most (primary and secondary values)
2. Consistent trade-offs (pairs of "chose X over Y" decisions)
3. Architectural metaphor (the dominant pattern in one image)
4. Philosophy contradictions (where stated values conflict with implementation)
5. Consistency model analysis (CAP positioning, consistency windows)
6. Complexity budget (cache % of codebase, proportionality verdict)
7. Failure modes inventory (entity cache: N modes, DataFrame cache: M modes)
8. Observability assessment (visible vs hidden state)
9. Cognitive load analysis (concept count, onboarding impact)

OUTPUT: Structured philosophy document with diagnostic assessments.
```

---

## 3. State Update

### Final State After Review

```yaml
state:
  phase: complete
  artifacts_produced:
    - ARCH-REVIEW-1-INDEX.md
    - ARCH-REVIEW-1-TOPOLOGY.md
    - ARCH-REVIEW-1-CACHE.md
    - ARCH-REVIEW-1-STEEL-MAN.md
    - ARCH-REVIEW-1-STRAW-MAN.md
    - ARCH-REVIEW-1-DEPENDENCIES.md
    - ARCH-REVIEW-1-DOMAIN-HEALTH.md
    - ARCH-REVIEW-1-PHILOSOPHY.md
    - ARCH-REVIEW-1-OPPORTUNITIES.md
    - ARCH-REVIEW-1-PYTHIA-DIRECTIVE.md
  output_directory: ".claude/wip/q1_arch/"
  findings_summary:
    essential_ratio: "70%"
    accidental_ratio: "30%"
    top_strengths: 5 (descriptor system, detection tiers, defensive caching, HolderFactory, query engine)
    top_concerns: 5 (triple registry, cache gap, hardcoded sections, import effects, caching density)
    opportunities: 5
    gaps: 7
    paradoxes: 5
```

### Artifacts Cross-Reference

| Artifact | Primary Agent | Input Sources |
|----------|-------------|---------------|
| INDEX | Context Engineer | All below |
| TOPOLOGY | Exploration agents 1-10 | Direct codebase reads |
| CACHE | Exploration agents 6-10 | Cache subsystem reads |
| STEEL-MAN | Topology steel-man, Dependency steel-man, Structure steel-man | Exploration data |
| STRAW-MAN | Topology straw-man, Dependency straw-man, Structure straw-man | Exploration data |
| DEPENDENCIES | Dependency steel-man + straw-man | Exploration data |
| DOMAIN-HEALTH | Structure steel-man + straw-man | Exploration data |
| PHILOSOPHY | Philosophy extractor | All exploration + analysis data |
| OPPORTUNITIES | Remediation synthesizer | All steel-man + straw-man outputs |
| PYTHIA-DIRECTIVE | Pythia | Session context |

---

## 4. Throughline

### Rationale for Bypassing Sequential Pipeline

The standard `arch` rite workflow is sequential: `topology-cartographer` -> `dependency-analyst` -> `structure-evaluator` -> `remediation-planner`. This is appropriate when each phase builds on the previous phase's output.

For this review, Pythia bypassed the sequential pipeline because:

1. **Exploration was already complete**: 10 agents had already mapped the codebase. The analysis phase did not need to discover -- it needed to evaluate.

2. **Anchoring prevention**: If topology analysis runs first, dependency analysis would be anchored by topology's framing. Parallel dispatch ensures each specialist forms independent assessments from the same raw data.

3. **Steel-man/straw-man requires parallel pairs**: You cannot run a steel-man analysis sequentially before a straw-man (or vice versa) without the second being influenced by the first.

4. **Time efficiency**: 8 parallel agents complete faster than 4 sequential phases, each waiting for the previous.

### Decisions Made

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| Parallel dispatch | Prevent anchoring, enable paired analysis | Sequential pipeline (standard) |
| 3 paired dimensions | Topology, dependency, structure cover all analysis needs | 2 pairs (merge dependency+structure) |
| Separate philosophy extraction | Philosophy is a cross-cutting concern, not a dimension | Include in remediation synthesis |
| 8 specialist agents | 6 paired + 2 synthesis covers all dimensions | Fewer agents with broader scope |

### Open Questions (Post-Review)

1. **Was 10-agent exploration sufficient?** -- Yes, based on synthesis completeness. No analysis agent reported missing data.

2. **Were specialist prompts specific enough?** -- Mostly yes. Some agents produced overlapping findings (e.g., both topology straw-man and structure straw-man identified the triple registry problem). This overlap was useful for validation but could indicate prompt overlap.

3. **Could synthesis reconcile conflicts?** -- Yes. The steel-man/straw-man pairs produced complementary rather than contradictory findings. The descriptor system, for example, was defended by steel-man (proportionate complexity) and not challenged by straw-man (it was not identified as a weakness).

4. **Methodology reusability** -- The parallel steel-man/straw-man dispatch pattern is reusable for any architectural review. The key insight is that balanced assessment requires simultaneous independent analysis, not sequential iterative refinement.
