---
type: review
status: proposed
critic: eunomia / verification-auditor (operator-ruled substitution for hygiene/audit-lead, 2026-08-13, in-session)
subject: PREDICATE-sayable-set-rev6-2026-08-13.md
author_under_review: 10x-dev / architect (EX-2, WS-4)
disjointness: eunomia != 10x-dev (Axiom-1 satisfied); this is a rite-disjoint NCSR, not a momentum swap
evidence_grade_ceiling: MODERATE
---

# CRITIQUE — say-able-set re-derivation (rev6) under R-4 and G4′

> **BINDING VERDICT: CONCUR** — with two NARROW anchor corrections (neither
> flips a disposition) and one ADDED refuter observation. The rev6 re-derivation
> is sound: it promotes nothing it cannot re-run the gates on, it corrects 1b's
> ground off the dead event-class-mismatch name, it disposes the
> `honest_contract_complete` vacuous-True explicitly (DR-9 + operator-route), and
> it surfaces Q-3 without resolving it. Every load-bearing code claim was
> **re-derived with my own hands** at this repo's working tree on `main`
> (HEAD `4129ae7e`); the author's SVR ledger was treated as CONTEXT, not
> evidence. Self-attestation capped **MODERATE** (in-fleet rite-disjointness is
> not external corroboration; static-code-read altitude only — no live CLI fired,
> per fences).

---

## §1 Verdict per EX-2 exit criterion

| # | Exit criterion | Verdict | Ground (own-hands) |
|---|---|---|---|
| 1 | Per-item G4′ branch table complete + single-signed where PASS claimed; assess ADDED branch 7 on 1a | **CONCUR** | 1a measurand branches 1-6 single-signed (only non-neutral = branch 6 OVERSTATE); branch 7 correctly segregated to a disclosure axis, NOT counted in the G4′ conjunction, routed to DR-9. 1b table vacuous-by-construction (fails G2 upstream) — correctly localized. §2.7 row 3 G4′-passes-on-value, withheld at G2. |
| 2 | 1b + §2.7 row 3 each carry explicit disposition with ground named | **CONCUR** | 1b: `WITHHELD-PENDING`, ground CORRECTED to carrier-gap (R-4 = no-op for 1b — confirmed). §2.7 row 3: `WITHHELD-PENDING`, reachable-not-say-able on a roster-exhibitability UV-P (R-4 genuinely bites — confirmed). |
| 3 | `honest_contract_complete` disposed explicitly (DR-9 + honest_empty routed) | **CONCUR** | Vacuous-True verbatim-confirmed; propagates into 1a DISCLOSURE + shipped `honest_empty` path, NOT into 1a's gates. DR-9 sound; shipped hazard correctly routed operator-ward, not absorbed. |
| 4 | Q-3 surfaced, not resolved | **CONCUR** | §6 surfaces "is G4′ the operator's intended gate?"; does not assume the answer; dispositions shown robust to the answer (they turn on carrier-existence / roster-exhibitability, not on G4′'s sign test). |

**On the ADDED branch 7 (assessment requested).** I CONCUR with the addition and
grade it a genuine tightening, not padding. Branch 7 (`honest_contract_complete`
read into the render as a completeness attestation, vacuously True on an empty
manifest) is a *different kind* of error (overstate-**completeness**) from the
measurand's branch 6 (overstate-**quiet-time**). The author does the correct
thing: keeps it OUT of the G4′ conjunction (G4′ is a measurand-sign gate — the
wrong detector for a completeness-attestation defect), preserves the honest
measurand PASS, and routes the defect to a bounded disclosure clause (DR-9). This
is exactly the completeness-vs-correspondence catch rev-5 and its critic missed.
It does **not** flip 1a to WITHHELD, and it should not: 1a's say-ability rests on
its four measurand gates, which do not read the field (§3 below); DR-9 constrains
the render. Correct call.

---

## §2 BINDING NR-2 — NCSR verdict: **STANDS, with NARROWED scope**

**Negative under test:** *"item 1b stays withheld — no shipped surface renders
its week-by-week edit series."* All four §A.2 refuters re-swept **own-hands** this
dispatch (I inherited none of the author's sweep). Per §A.3: what each returned
incl. NULLS, the hop one past where the argument stops, and the refuter I ADDED.

| refuter | own-hands result | hop one past (named) |
|---|---|---|
| **(a)** `DEFAULT_STORY_TYPES` beyond `section_changed` | **FIRED + fully swept; does NOT promote.** `cache/integration/stories.py:23-33` = **9 subtypes, 6 edit-class** verbatim (`assignee_changed, due_date_changed, marked_complete, marked_incomplete, enum_custom_field_changed, number_custom_field_changed`); the other 3 (`section_changed, added_to_project, removed_from_project`) are move/membership-class. Cache-miss writes the stream **unnarrowed** (`stories.py:143` `fetcher(task_gid, None)` full fetch → `:145` `set_versioned`). Edit history **IS** retained — this kills the "not constructible" name. Retention ≠ exposure. | Terminal read-time narrowing at `services/section_timeline_service.py:341` (`resource_subtype == "section_changed"`). I re-swept for a *second* consumer: `filter_stories_by_type` (`stories.py:294`, `include_types` param) has **ZERO callers**; the only cached-story consumers reaching computation are the section-timeline service (narrows to `section_changed`, emits move-class scalars) and `story_warmer.py:91` (a **writer**, not a surface). The second timeline call site `:511` is a cache-miss backfill that re-reads through the same `:341` narrowing. **No shipped surface exposes the 6 edit-class subtypes as a series.** |
| **(b)** retained frame snapshots (`dataframe_cache_put`) | **NULL** (confirmed the negative). `cache/dataframe/tiers/memory.py:133-159`: `put` pops any existing key (`:144-146`) before adding — single current entry, LRU-evicted; key is `entity_type:project_gid` (`:137`), **no time partition**. `cache/dataframe/tiers/progressive.py:279` `put_async` keys identically (`:286` `"{entity_type}:{project_gid}"`). No snapshot log to walk. | `created_at` is per-entry eviction/staleness metadata, not a partition key — there is no historical frame-snapshot series to reconstruct a week-by-week edit history from. |
| **(c)** any OTHER shipped field with edit-class series semantics | **NULL** (confirmed). `models/business/section_timeline.py:158-212` `OfferTimelineEntry` = **7 scalars** (`offer_gid, office_phone, offer_id, active_section_days, billable_section_days, current_section, current_classification`) — all id/dwell/current-state, `model_config extra="forbid"` (`:212`), **no transition fields**. | The only shipped edit-class datum is `last_modified` on `/rows` — a **current snapshot** (`dataframes/schemas/base.py:76-82`, `nullable=False`, `source="modified_at"`); `max`-reducible to current state (item 1a) but carries no prior values to form a series. |
| **(d)** `honest_contract_complete` vacuous-True → item 1a | **FIRED into 1a's DISCLOSURE, NULL into 1a's GATES** (confirmed the crux). See §3. | The served boundary `api/routes/query.py:517` (`S7_CAUSE_HONEST_REFUSAL`); whether an empty/never-built manifest **reaches** it in production is the unprobed UV-P (correctly carried, not asserted). |

**Refuter I ADDED (§A.3 duty).** On §2.7 row 3's live-proxy branch: beyond the
author's two-clock rejection, the shipped roster-list endpoint is **S2S-scoped to
the pinned cutover project** (`api/routes/projects.py:377` `list_sections`, via
`get_s2s_section_client`, allowlist `projects.py:61`). This is a **second,
independent** reason the live proxy cannot serve as a general roster source — it
is not an arbitrary-project read at all. This **strengthens** the WITHHELD
disposition; it does not weaken it.

**NR-2 verdict: STANDS — NARROWED.** *"Item 1b stays withheld"* STANDS. The ground
narrows exactly as the author states: not "the event-class mismatch is
undissolvable" (refuter (a) dissolved that name — edit history is retained) but
"no shipped response field carries the retained edit series, and R-4's read grant
does not reach the story cache" (refuters (b),(c) both NULL). No refuter promoted
1b. No promotion was made anywhere, so there is nothing to revert (PT-04 clause
satisfied vacuously).

---

## §3 Own-hands confirm of the vacuous-True → item 1a propagation (crux for 1a)

- **Vacuous-True — CONFIRMED verbatim.** `dataframes/section_persistence.py:268-269`:
  `if not manifest.sections: return True` (inside `is_honest_complete()`, the AC-3
  derivation site); docstring `:266`: *"An empty manifest (no sections) returns True
  (vacuously complete)."* It is a **failure-absence** receipt (`True` = "no section I
  know about is FAILED"), never a **correspondence** receipt.
- **Into 1a's DISCLOSURE — FIRED.** The field is spread into `RowsMeta`
  (`query/engine.py:292` `honest_contract_complete=honest_contract_complete`) and
  R-4:60 permits 1a's render to read it off `meta`. A render presenting `True` as
  "roster complete / genuinely quiet" is false on an empty/never-built manifest —
  the alias defect DR-9 closes. Confirmed.
- **Into 1a's GATES — NULL.** 1a's measurand `now − max(last_modified)` derives
  from the `last_modified` column (`base.py:76-82`), and its G2 denominator is the
  N sections holding offer rows computed consumer-side from the `/rows` payload —
  **both independent of `honest_contract_complete`**, which is a sibling `RowsMeta`
  field. On an empty manifest the readout is **empty (N=0), not wrong** — exhibitable,
  not overstated. None of 1a's four say-ability gates read the field. Confirmed.
- **Shipped `honest_empty` hazard — correctly REFERENCED not absorbed.**
  `query/engine.py:280` `honest_empty = honest_contract_complete and prefilter_row_count == 0`
  → consumed at `query.py:515-519` (`S7_CAUSE_HONEST_REFUSAL if getattr(result.meta,
  "honest_empty", False)`). A vacuous-True empty manifest with zero rows would be
  attested a genuine empty-200 rather than a still-building 503 — a directional
  false-freshness hazard in shipped code. This is product correctness, not
  say-ability; routing it operator-ward (§6.1) and carrying the reachability as a
  UV-P (not asserting the round-trip) is the correct disposition.

**Item 1a remains `SAY-ABLE`.** Its four gates are untouched by the vacuous-True;
its render acquires the DR-9 non-aliasing constraint (ratification is the
operator's / disclosure-contract owner's, correctly reserved).

---

## §4 NARROW corrections (recorded; neither flips a disposition)

1. **Anchor drift — vacuous-True.** SVR-R6-4 / §3.3 cite `section_persistence.py:270-271`
   (docstring `:267`); the actual lines are **:268-269** (docstring **:266**), ~2-line
   drift. Marker text is verbatim-correct; substance fully confirmed. Cosmetic.
2. **Anchor imprecision — shipped roster list endpoint.** §2.3 branch 4 / §3.2 /
   SVR-R6-8 cite "verified shipped, `api/routes/sections.py:50`" for
   `GET /api/v1/projects/{gid}/sections`. `sections.py:50-84` is the **single-GID**
   `GET /api/v1/sections/{gid}`; the LIST endpoint actually lives at
   **`api/routes/projects.py:370-390`** (`list_sections`) and is **S2S-scoped to the
   pinned cutover project**. The substance (a shipped live-proxy roster read exists,
   two-clock vs the ≤4h frame) HOLDS; the disposition (`WITHHELD`, reject two-clock)
   is robust and, per §2's ADDED refuter, *strengthened* by the scoping. Correct the
   file:line and note the scoping; the verdict does not move.

---

## §5 Fences attestation (this dispatch)

- **CR-1** — no Asana / live-board write. None fired.
- **CR-2** — `s3://autom8y-asr-verdicts` not read or listed. None.
- **CR-5** — no credential material encountered; no `git log -p` / `git show` on
  `a578ca85` / `525431de` / `15cffee1`; no authenticated call. Only `git rev-parse
  HEAD` + `git branch` (state reads).
- **Monorepo trap** — read only the `autom8y-asana` working tree (authoritative per
  4b converse: absence-from-git ≠ absence). Did NOT read the divergent `autom8y`
  monorepo.
- **C-9** — nothing unruled is recorded here as decided. DR-9 ratification, the
  `honest_empty` hazard, the roster probe, and the S4 enumeration-addition are all
  surfaced-not-decided (author §6; concurred).
- No infra mutation; no git write/commit/push.

---

## §6 Evidence & self-attestation

| claim | grade | basis |
|---|---|---|
| refuters (a)-(d) re-swept incl. NULLs | **MODERATE** | own-hands file-reads (§2,§3); rite-disjoint (eunomia≠10x-dev) but in-fleet — not external corroboration; static-read altitude only |
| vacuous-True → 1a: disclosure FIRED / gates NULL | **MODERATE** | `section_persistence.py:268-269`, `engine.py:280/292`, `query.py:515-519`, `base.py:76-82` re-read own-hands |
| 1b `WITHHELD` ground = carrier-gap (R-4 no-op for 1b) | **MODERATE** | `stories.py:23-33/143-145`, `section_timeline_service.py:341/511`, zero callers of `filter_stories_by_type` — code-read decisive; offer-task populate-link unprobed (UV-P) |
| §2.7 row 3 `WITHHELD`, reachable; list endpoint S2S-scoped | **MODERATE** | `projects.py:370-390` re-read; roster single-clock-exhibitability UV-P by construction |
| item 1a `SAY-ABLE` stands; DR-9 required | **MODERATE** | gate-independence traced own-hands |

STRONG language is prohibited here (self-ref ceiling; no non-knossos external
corroboration). No claim above is graded above MODERATE.

**Disposition: CONCUR.** rev6 is fit to stand as the say-able-set revision of
record, subject to the two NARROW anchor corrections in §4 (editorial; no
disposition moves) and the author's own operator-reserved routes (§6 of the
subject). Item 1a remains SAY-ABLE; 1b and §2.7 row 3 remain WITHHELD-PENDING on
their correctly-named surviving grounds; the negative under NR-2 STANDS-NARROWED.
