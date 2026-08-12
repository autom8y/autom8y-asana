---
type: review
status: accepted
artifact_id: PROBE-pt01-c5-and-edit-history-2026-08-12
initiative: asana-native-insight-delivery
date: 2026-08-12
run_by: main thread, discharging two probes PT-01 named and could not run (Read-only seat)
discharges: PT-01 §7 item 2 (C-5) · PT-01 §6 prediction, refuter (ii)
grade: STRONG on C-5 · PARTIAL on the edit-history sweep (scope stated below)
---

# PROBE — PT-01's C-5, and its predicted next false negative

PT-01 returned `SPINE COHERENT WITH CONDITIONS` from a Read-only seat and named
two things it could not check. Both are cheaper than the decisions resting on
them. Both were run read-only against this repo's `origin/main`.

---

## 1. C-5 — **CONFIRMED. Item 2's G4 justification is refuted.**

PT-01 derived, from artifact descriptions alone, that item 2's error direction
claim is wrong. The implementation confirms it exactly.

**The imputation produces exactly one interval, at the CURRENT classification**
(`services/section_timeline_service.py:272-300`):

```python
return [SectionInterval(section_name=section_name,
                        classification=account_activity,   # ← CURRENT classification
                        entered_at=task_created_at,
                        exited_at=None)]
```

**The two day-counts are classification-set filters over those intervals**
(`models/business/section_timeline.py:79-104`):

```python
active_days_in_period   → _count_days_for_classifications(start, end, {ACTIVE})
billable_days_in_period → _count_days_for_classifications(start, end, {ACTIVE, ACTIVATING})
```

**Therefore, for an imputed offer whose current classification is ACTIVE:**

| quantity | value |
|---|---|
| the single interval | ACTIVE, `[created_at, None]`, spanning the whole window |
| `active_section_days` | full window |
| `billable_section_days` | full window (ACTIVE ∈ the billable set) |
| **`billable − active`** | **0** |

Item 2's measurand is `billable_section_days − active_section_days` — dwell in
ACTIVATING. If that offer was in fact in ACTIVATING for part of the period, the
true value is positive and **the readout reports zero**.

**That is an UNDERSTATEMENT**, produced by the same imputation S1 rev-3 cites at
`PREDICATE…:890` as *"one-directional (dwell **overstated**, never
understated)"*.

**Consequence.** G4 is the gate that requires imprecision be **bounded and its
direction declared**. Item 2's declared direction is wrong, and the true
behaviour is **sign-ambiguous** — it overstates for offers currently in
ACTIVATING and understates for offers currently in ACTIVE, on the same call.
Item 2's `SAY-ABLE` verdict **rests on a refuted G4 ground** and must be
re-derived. *(This is a defect in the justification, not necessarily in the
verdict — a re-derivation may still pass G4 on honest, sign-declared terms, or
may pass once imputation is disclosed. It must not stand as written.)*

**The sharper general statement**, superseding the duration/occurrence split in
`FINDING-option-g-imputation-indistinguishable-2026-08-12.md`:

> Option (g) is sound for durations measured **in the offer's current
> classification**, and **sign-ambiguous** for durations derived as
> **differences across classifications** — because imputation collapses the
> offer's entire history into its present classification.

---

## 2. PT-01's predicted next false negative — **refuter (ii) FIRES**

PT-01 predicted the spine's next error would be another **false negative**, and
named S1's surviving cost tier (iii) — *"**edit** history is genuinely absent and
not constructible"* (`PREDICATE…:1196-1199`) — as the claim most likely to fall.
It named two un-swept refuters. The second one fires.

**`DEFAULT_STORY_TYPES` has NINE members, not one** (`cache/integration/stories.py:23-33`):

```
assignee_changed · due_date_changed · section_changed · added_to_project ·
removed_from_project · marked_complete · marked_incomplete ·
enum_custom_field_changed · number_custom_field_changed
```

Every downstream conclusion in this spine used exactly one member —
`section_changed` — because that is what `section_timeline_service.py:341`
filters on. **Four of the other eight are edit-class events**, and two of them
(`enum_custom_field_changed`, `number_custom_field_changed`) are *custom-field
edits*, which is the closest thing to the "edit history" declared absent.

The module states the rationale itself (`stories.py:266-267`): *"Per ADR-0021,
struc computation uses specific story subtypes that track task state changes."*
These subtypes are **enumerated as relevant by design**, not incidental.

### ⚠ Scope of this refutation — stated precisely, because over-claiming here would repeat the error in reverse

**What IS established**: the system enumerates nine story subtypes as relevant,
four are edit-class, and this spine's entire edit-history reasoning rested on
one of them. **S1's tier (iii) claim — "genuinely absent and not constructible"
— is therefore NOT established**, and the evidence points against it.

**What is NOT established**: `filter_relevant_stories` (`:266-297`) is a
**read-time filter over an already-fetched list**, with `DEFAULT_STORY_TYPES` as
its default `include_types` (`:292`). I did **not** verify that the offers
project's warm path actually fetches and caches these subtypes. A type being
enumerated as relevant is not proof it is present for this entity class.

**So the honest verdict is: "uncontracted and unverified, NOT absent"** —
precisely the correction S4 was forced into on its own negative result, arriving
one sprint later at the adjacent claim. **The next probe** — *does the offers
warm path cache the edit-class subtypes?* — is one grep plus one cache read, and
it decides whether tier (iii) is refuted outright or merely unproven.

**Refuter (i) — the retained frame snapshots — was NOT swept.** PT-01 identified
`dataframe_cache_put` (`cache/integration/dataframe_cache.py:976`, plus
`:926`/`:955` variants) as a live emission and noted the S1 critic had routed the
frame-diff question to S4, which never enumerated it. That would be **option
(h)**. It remains open and is the larger of the two.

---

## 3. What this means for the gate and the fork

- **C-5 fires as PT-01 specified.** Item 2's G4 ground must be re-derived. Two of
  the three `SAY-ABLE` readouts (2 and 5a) already carried the caveat that they
  moved on grounds no critic had seen; one of those grounds is now refuted.
- **PT-01's error-class diagnosis is corroborated on its first prediction, at
  the first place it looked.** That is the strongest evidence in the record that
  the pattern is structural — a property of how the spine was charged — and not
  three seats being unlucky. The mechanism it named holds: *the receipt grammar
  cannot express a negative, so a true scoped probe and a false general claim
  are indistinguishable at review time.*
- **The option slate is not closed.** S4 graded option-space completeness at
  MODERATE and explicitly declined to treat seven as closure. That caution is
  now vindicated: option (h) is un-swept, and the edit-history tier is unproven
  rather than refuted. **GATE-FORK should be told the slate is open**, not that
  it is seven.

## Verification scope

Read-only: source at this repo's `origin/main`. No HTTP request, no endpoint
call, no Asana call, no cache read, no mutation of any kind. The two questions
left open above are named, not inferred.
