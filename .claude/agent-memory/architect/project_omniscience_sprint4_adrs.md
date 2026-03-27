---
name: Omniscience Sprint 4 ADRs
description: Two ADRs produced for Sprint 4 -- registry unification (TENSION-013) and descriptor-driven resolver (TENSION-016)
type: project
---

Sprint 4 of Project Omniscience produced two ADRs for the 10x-dev implementation phase:

1. **ADR-omniscience-registry-unification** (`.ledge/decisions/ADR-omniscience-registry-unification.md`): Facade-first migration to collapse ProjectTypeRegistry and EntityProjectRegistry into delegation facades over EntityRegistry. 4 phases: facade ProjectTypeRegistry, facade EntityProjectRegistry, equivalence validation, remove independent registration. registry_validation.py (R-005) stays active throughout.

2. **ADR-omniscience-descriptor-driven-resolver** (`.ledge/decisions/ADR-omniscience-descriptor-driven-resolver.md`): Add `custom_field_resolver_class_path` to EntityDescriptor. Eliminates TENSION-016 hardcoded allowlist in universal_strategy.py:935. Extends custom field resolution to contact, asset_edit, asset_edit_holder (previously excluded).

**Why:** Phase A (SRE cascade foundation) is complete per handoff at `.ledge/spikes/omniscience-sre-handoff.md`. Sprint 4 begins Domain 1 (Matching) by resolving the two tensions that block descriptor-driven entity behavior.

**How to apply:** Principal-engineer implements from these ADRs. Both are Phase 1/Sprint 4 scope. Phase 4 of registry unification is gated behind production equivalence validation.
