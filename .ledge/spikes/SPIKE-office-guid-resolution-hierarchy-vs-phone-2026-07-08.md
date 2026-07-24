---
type: spike
status: proposed
---

# SPIKE — office-guid resolution: task-hierarchy is authoritative, phone is a lossy proxy

- Date: 2026-07-08 (floodgates batch — Total Wellness Center held fail-closed)
- Trigger: PLAY 1215766139321621 refused — `2 Business tasks match office_phone='+13036277995'`

## The gap

`onboarding_walkthrough/template_comment.py::_resolve_office_guid` (and its
`contact_synthesis._business_gid_by_phone` bridge) resolve the receiver business by
**office_phone → workspace /tasks/search → filter to Businesses-project members**. Phone is
NOT unique: a practice's BUSINESS card and its OPPORTUNITY/lead card share it. For Total
Wellness Center, `+13036277995` matches both `1214127219419742` (BUSINESS, section BUSINESSES)
and `1214420107547660` ("Holly R. Geersen, DC", section OPPORTUNITY) — same practice (business
Owner Name = "Dr. Holly Geerson"). Two hits after the discriminator → correct fail-closed refuse.

## The authoritative link was in the task tree

```
PLAY 1215766139321621  "PLAY: Custom Calendar Integration — Total Wellness Center"
  └─ parent 1214127290389479  "Total Wellness Center PLAYS/REQUESTS ✅"
       └─ parent 1214127219419742  "Total Wellness Center"  [BUSINESS_PROJECT member]
              Company ID = 7363c7ea-66f8-487f-9f6e-c7a12a63d33f
```
A PLAY has exactly ONE business ancestor. The parent chain is the ownership relation; phone is a
fragile proxy that aliases across a practice's multiple cards.

## What already exists in autom8y-asana (reuse, don't re-mint)

- `cache/policies/hierarchy.py::get_ancestor_chain(gid, max_depth)` -> [parent..root]; `get_root_gid`.
- `dataframes/resolver/cascading.py::_traverse_parent_chain`, `warm_parents`, `_get_parent_gid`.
- `cache/providers/unified.py::get_parent_chain_async`, `_warm_ancestors`.
- `core/project_registry.py::BUSINESS_PROJECT = "1200653012566782"` (Businesses root hierarchy).
- `core/entity_registry.py` — "business" -> EntityType.BUSINESS typing.
The walkthrough resolver used none of these; it re-minted a phone bridge.

## Fix direction

Primary resolution: walk the PLAY ancestor chain, take the first ancestor that is a
`BUSINESS_PROJECT` member, read its Company ID custom field. Phone becomes a fallback /
cross-check only. Closes the collision CLASS (any practice with an opportunity card sharing the
office phone). Proof-of-fix driver (`scratchpad/fg_twc_hierarchy.py`) injects exactly this walk
via monkeypatch of `_resolve_office_guid` — no production edit — and drives TWC through the real
office_runner produce/resume path.

## Follow-ups (substrate queue)

- Port the ancestor-walk into `_resolve_office_guid` (production build + 2-sided QA: TWC resolves
  via hierarchy; a phone-only case still works via fallback).
- `api/routes/intake_resolve.resolve_business` is also phone-only (GidLookupIndex) — same latent
  class for any hierarchy-rooted caller; evaluate a hierarchy-aware overload.
