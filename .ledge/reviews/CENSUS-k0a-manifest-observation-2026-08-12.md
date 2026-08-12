---
type: review
status: accepted
artifact_id: CENSUS-k0a-manifest-observation-2026-08-12
initiative: offers-freshness-axis-contract
precondition: K-0a
rite: eunomia
date: 2026-08-12
verdict: PASS
---

# CENSUS — K-0a / B3-a manifest observation

Rite-disjoint seat (eunomia / verification-auditor) executing the precondition
assigned by name at `ADR-007-verification-axis-gate-2026-08-12.md:1134`, against
the P-5-rescoped criteria block at `:1144-1149`. The annex's criteria were **not**
used; the population measured is the full 27, row-bearing and zero-row alike.

`now` for every age in this document was taken at **`2026-08-12T20:54:08Z`**
(receipt: `date -u` immediately preceding the S3 GET, §5 step 4).

---

## 1. VERDICT

**PASS.** All 27 names in `OFFER_CLASSIFIER.sections_for(ACTIVE, ACTIVATING)`
resolve to a manifest section, all 27 carry a non-null `last_verified_at`, and
`now − oldest_stamp` over the full classified population is **1 231 s = 20.5 min
= 0.34 h** — hours, not days, and comfortably inside the measured build cadence
(mean stamp-advance gap 0.55 h, max 2.43 h over a 42-version / 16.9 h window).

The pinned-floor scenario the criteria were pre-registered to detect
(§4.5, `ADR-007:1151-1155`) is **not present** at the observed instant, and was
not present in any of 45 distinct manifest versions I read spanning 2026-08-08
through 2026-08-12.

This is a PASS on all three criteria plus B3-b. It is **not** an unqualified
clean bill: §2 criterion 3 records a real, observed partial-stamp-pass at
minutes scale, and §6 names three things I could not determine.

---

## 2. The three criteria

### The object I read

| field | value |
|---|---|
| bucket | `autom8-s3` |
| key | `dataframes/1143843662099250/offer/manifest.json` |
| VersionId | `oPgh8BcwAeSNCpFSxUNEYAE43TlLbTCA` |
| ETag | `bc69af49278ee4b8be324e69603b3bf3` |
| LastModified | `2026-08-12T20:33:37+00:00` |
| ContentLength | 15 210 |
| `entity_type` | `offer` |
| `project_gid` | `1143843662099250` |
| `schema_version` | `1.6.0` |
| `total_sections` / `completed_sections` | 34 / 34 |

Key derivation receipts (all pinned at `origin/main` = `4129ae7e`, which equals
this worktree's `HEAD`; `git diff --stat origin/main HEAD -- src/` is empty):

- bucket literal `autom8-s3` — `src/autom8_asana/settings.py:427`
- prefix literal `dataframes/` — `src/autom8_asana/storage_namespace.py:284`
- key shape `{prefix}{project_gid}/{entity_type}/manifest.json` —
  `src/autom8_asana/dataframes/section_persistence.py:375`
- `project_gid="1143843662099250"` on the offer classifier —
  `src/autom8_asana/models/business/activity.py:183`

**CR-2 fence: not touched.** The path to these answers does not run through
`autom8y-asr-verdicts`. That bucket was neither read nor listed. The producer-side
offers manifest answered both questions from one object, exactly as `ADR-007:1158`
predicted.

### Criterion 1 — do all 27 classified names resolve to a manifest section?

**PASS. 27 / 27 resolve. 0 unresolved.**

The classifier map is at `src/autom8_asana/models/business/activity.py:181-230`
(`active` block `:185-208`, 22 names; `activating` block `:209-215`, 5 names).
I verified this rather than inheriting the parallel seat's `179-231` — the
assignment statement begins at `:181` and the closing paren is `:230`; `:179-231`
brackets the same block with two lines of slack, so the parallel seat's citation
is correct in substance and loose by two lines at each end.

`sections_for` returns **lower-cased** keys (`activity.py:76-86`; the mapping is
lower-cased at construction, `activity.py:118-121`), so resolution is
case-insensitive against `SectionInfo.name`. That is the same normalisation the
shipped reducer uses (`metrics/freshness.py:801`), so the join semantics I applied
are the production join semantics, not an auditor's convenience.

Result over the 27, at VersionId `oPgh8Bcw…`:

| name | class | rows | status | `last_verified_at` |
|---|---|---:|---|---|
| ACTIVATING | activating | 23 | complete | 2026-08-12T20:33:36.848152Z |
| ACTIVE | active | 45 | complete | 2026-08-12T20:33:36.848152Z |
| AWAITING ACCESS | activating | 0 | complete | 2026-08-12T20:33:36.848152Z |
| CALL | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| IMPLEMENTING | activating | 22 | complete | 2026-08-12T20:33:36.848152Z |
| LAUNCH ERROR | activating | 0 | complete | 2026-08-12T20:33:36.848152Z |
| MANUAL | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| NEW LAUNCH REVIEW | activating | 3 | complete | 2026-08-12T20:33:36.848152Z |
| ONE-OFF | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE - Human Review | active | 7 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUALITY - Pending Leads and/or Update Targeting | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUALITY - Poor Show Rates | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUALITY - Update Targeting | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUANTITY - Decrease Lead Friction | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUANTITY - Request Asset Edit | active | 1 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUANTITY - Update Offer Name | active | 10 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUANTITY - Update Offer Price Too High | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| OPTIMIZE QUANTITY - Update Targeting of Proven Asset | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| PENDING APPROVAL | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| REJECTIONS / REVIEW | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| RESTART - Pending Leads | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| RESTART - Request Testimonial | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| REVIEW OPTIMIZATION | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| RUN OPTIMIZATIONS | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| STAGED | active | 4 | complete | 2026-08-12T20:33:36.848152Z |
| STAGING | active | 0 | complete | 2026-08-12T20:33:36.848152Z |
| SYSTEM ERROR | active | 0 | complete | 2026-08-12T20:33:36.848152Z |

**Population cross-check — the ~19 figure lands exactly.** Of the 27, **19 are
zero-row** and 8 are row-bearing. `ADR-007:1141-1142` says the annex's criteria
"would have excluded … exactly the ~19 zero-row sections". The measured count is
**19**. That is an independent confirmation that the population I measured is the
population P-5 rules must be included, and that I did not use the superseded
criteria. The 19 zero-row names are:

```
awaiting access · call · launch error · manual · one-off
optimize quality - pending leads and/or update targeting
optimize quality - poor show rates · optimize quality - update targeting
optimize quantity - decrease lead friction
optimize quantity - update offer price too high
optimize quantity - update targeting of proven asset
pending approval · rejections / review · restart - pending leads
restart - request testimonial · review optimization · run optimizations
staging · system error
```

### Criterion 2 — does every one of those 27 carry a non-null `last_verified_at`?

**PASS. 27 / 27 non-null. 0 null-stamp.**

Zero criterion-2 failures. This is the distinct failure mode from criterion 1 and
I kept them apart deliberately: per `ADR-007` §2.3(b) an absent stamp is
AXIS-NULL → ABORT, so a null here would have meant something different from a
non-resolving name. Neither occurred.

Also **zero null stamps across all 34 manifest sections**, not merely the 27 —
including the 7 sections classified `inactive`/`ignored`, which are out of the
P-5 denominator but were checked as a free by-product of reading the object.

Field receipt: `SectionInfo.last_verified_at` is declared at
`src/autom8_asana/dataframes/section_persistence.py:112`, with the collision
warning against `cache/models/freshness_stamp.py` at `:106-111`. I read the
manifest-tier field, which is the one the criteria name.

### Criterion 3 — is `now − oldest_stamp` over the full set hours, not days?

**PASS. 1 231 s = 20.5 min = 0.34 h.**

```
now                      = 2026-08-12T20:54:08Z   (date -u, taken at GET time)
oldest stamp over the 27 = 2026-08-12T20:33:36.848152Z
newest stamp over the 27 = 2026-08-12T20:33:36.848152Z
now − oldest             = 1231.15 s = 20.52 min = 0.342 h = 0 days
intra-set spread         = 0.0 s (all 27 identical to the microsecond)
```

A single instant is a weak instrument for a criterion phrased against a *cadence*,
so I bounded it rather than asserting from one sample. I swept **every** version of
this object written since `2026-08-12T04:00:00Z` — 42 versions over 16.9 h — and
extracted the stamp state from each:

| measure | value |
|---|---|
| versions read in window | 42 |
| distinct stamp values | 31 |
| versions with any unresolved classified name | **0** |
| versions with any null stamp | **0** |
| mean stamp-advance gap | 1 985 s = **0.55 h** |
| **max stamp-advance gap** | 8 746 s = **2.43 h** |
| max `object_write − oldest_stamp` observed in window | 8 747 s = **2.43 h** |

So the worst case a consumer could have observed anywhere in that 16.9 h window is
**2.43 h**, not merely the 0.34 h at my sampling instant. Criterion 3 passes on the
window bound, not only on the sample. Hours, not days, by roughly two orders of
magnitude of margin against "days".

I extended the check backwards to four days at coarser resolution. Three additional
versions, each read in full:

| version LastModified | sections | unresolved | null-stamp | oldest stamp over 27 | intra-set spread |
|---|---:|---:|---:|---|---:|
| 2026-08-11T22:05:06Z | 34 | 0 | 0 | 2026-08-11T22:05:05.615581Z | 0.0 s |
| 2026-08-10T12:20:29Z | 34 | 0 | 0 | 2026-08-10T12:06:33.079523Z | 0.0 s |
| 2026-08-08T16:01:04Z | 34 | 0 | 0 | 2026-08-08T16:01:03.613956Z | 0.0 s |

**45 distinct manifest versions read. Zero criterion-1 failures. Zero criterion-2
failures. Zero stamps older than 2.43 h relative to their own object write.**

#### Observed, and reported rather than smoothed: the stamp pass is not always uniform

Criterion 3 is a detector for "the stamp pass is not reaching some section". At
days/weeks scale it did not fire. At **minutes** scale it did, in 3 of the 42 swept
versions, and I am recording it because averaging it away is exactly the failure
mode the charge warned against:

| version | sections at newest stamp | laggard(s) | lag |
|---|---:|---|---:|
| 2026-08-12T09:43:58Z | 26 / 27 | `ACTIVE` (45 rows) | 1 213 s (20.2 min) |
| 2026-08-12T10:04:18Z | 26 / 27 | `ACTIVE` (45 rows) | 1 213 s (20.2 min) |
| 2026-08-12T18:44:38Z | 25 / 27 | `OPTIMIZE QUALITY - Poor Show Rates` (0 rows), `RESTART - Request Testimonial` (0 rows) | 1 017 s (17.0 min) |

Each laggard cleared on a subsequent write. The lag is one build cycle, not a
pinned floor. **This does not change the verdict** — every one of these states is
still well inside "hours, not days" — but it establishes empirically that the
stamp pass has non-uniform coverage across a single write, that both row-bearing
and zero-row sections can be the laggard, and that the mechanism the criteria
were written to catch is live and observable at small amplitude. If it ever
acquires a section that never clears, criterion 3 becomes a FAIL.

The stamp pass has three documented skip branches at
`src/autom8_asana/dataframes/builders/progressive.py:511-573` — `PROBE_FAILED`
(`:515-516`), a delta-requiring verdict whose delta did not apply
(`:517-519`, Decision-5c), and the P3 null-watermark hash-only-CLEAN heal-and-
`continue` (`:561-572`). Any of the three would produce exactly this signature.
**I did not determine which one fired**; attributing it would require the warm-path
logs, which I did not read. Recorded as observation, not diagnosis.

---

## 3. B3-b — is `SectionInfo.name` populated?

**PASS. 34 / 34 populated. Zero nulls.**

Field declared at `src/autom8_asana/dataframes/section_persistence.py:92`
(`name: str | None = None`). At VersionId `oPgh8Bcw…` every one of the 34 entries
carries a non-null, non-empty string name. No duplicate names: the 34 GIDs map to
34 distinct lower-cased names, so the name-keyed join the reducer performs
(`metrics/freshness.py:801`) is unambiguous — one classifier name never resolves
to two manifest sections.

Same result in all three historical versions checked (2026-08-11, -10, -08): 34
sections, 34 names. B3-b's block on the metrics CLI (`ADR-007:1157`) is clear on
this evidence.

The §2.6 / Decision-7a contract assertion that would alarm on a null name
(`progressive.py:596-624`) therefore has nothing to fire on for this project today.

---

## 4. R-O8's question — is classifier-vocabulary drift a live risk today?

**No. Zero drift, in both directions, at the observed instant and across all 45
versions read (2026-08-08 → 2026-08-12).**

`RULING-operator-adr007-ratification-2026-08-12.md:25` puts R-O8 on HOLD with
revisit trigger "K-0a census result (do all 27 classified names resolve today)".
The answer is: **all 27 resolve. No name fails to resolve. There is no name to
report.**

I checked the reverse direction as well, which R-O8 does not ask for but which
bears on the same risk surface — a section the manifest carries that the classifier
does not know:

| direction | count | result |
|---|---:|---|
| classifier ACTIVE+ACTIVATING → manifest section | 27 | **27 resolve, 0 unresolved** |
| classifier full vocabulary (all four classes, lower-cased-distinct) → manifest | 34 | **34 resolve, 0 unresolved** |
| manifest section → known to classifier | 34 | **34 known, 0 unknown** |

The classifier's full distinct lower-cased vocabulary is exactly 34 names
(22 active + 5 activating + 3 inactive + 6 ignored = 36 raw, of which
`Plays`/`PLAYS` and `Performance Concerns`/`PERFORMANCE CONCERNS` collapse under
lower-casing to 34). The manifest holds exactly 34 sections. The two sets are in
**exact bijection**. There is no classifier name without a manifest section and no
manifest section without a classifier name.

**One honest qualification on this answer, and it matters for how far R-O8 can
lean on it.** Criterion 1 as written asks whether the names resolve to a *manifest*
section, and that is precisely what I measured. R-O8's underlying worry is phrased
against *Asana* — "a name in the classifier that Asana no longer has". The manifest
is the producer's cache of Asana's section set, not Asana. Its `name` field is
sourced from a live Asana section listing (`progressive.py:1065-1067`,
`{s.gid: s.name for s in sections}`), but the re-seed pass that writes it into an
existing manifest is gated on `info.name is None` (`progressive.py:505`), and
`mark_section_complete` only overrides the name when a fresh one is supplied on a
refetch (`section_persistence.py:206, 214`). **A same-GID rename in Asana would
therefore not propagate into the manifest until that section is refetched**, and
during that interval my criterion-1 check would read clean against a stale name.
A section *added* or *removed* in Asana does move the GID set, which is rebuilt
live each build, so that class of drift is visible.

I did not probe live Asana. The bijection above is strong evidence against drift
(a drifted classifier would have to be drifted in a way that the manifest happens
to mirror exactly), but it is not the same claim as "the Asana API returns these
34 names today". Stated so the operator can weigh R-O8 on what was actually
measured.

---

## 5. Method — exactly what I ran

Reproducible by a reader who distrusts me. Every step is read-only.

1. **Read the criteria verbatim before anything else** —
   `Read(.ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md, offset 1100, limit 200)`,
   covering §7.2 `:1130-1171` (precondition table, the ⚠ P-5 rewrite block, the
   B3-a three criteria, B3-b split, owner rationale, the standing UV-P) and §7.3
   `:1172-1206`. Then
   `Read(.ledge/decisions/RULING-operator-option4-interview-2026-08-12.md)` — P-5
   at `:23` — and
   `Read(.ledge/decisions/RULING-operator-adr007-ratification-2026-08-12.md)` —
   R-O8 at `:25`.

2. **Confirm the read surface is `origin/main`.**
   ```
   git rev-parse --abbrev-ref HEAD  -> main
   git rev-parse HEAD               -> 4129ae7e1dd59ad2d7049673762a5f58f9aca5b4
   git rev-parse origin/main        -> 4129ae7e1dd59ad2d7049673762a5f58f9aca5b4
   git diff --stat origin/main HEAD -- src/   -> (empty)
   ```
   HEAD equals `origin/main` and `src/` carries no drift, so the monorepo trap
   (`ADR-007` O-11, `:1295`) does not bite in this repo. I nevertheless extracted
   the classifier through `git show origin/main:…` rather than reading the
   worktree file, so the enumeration is pinned to `origin/main` by construction:
   ```
   git show origin/main:src/autom8_asana/models/business/activity.py > $SCRATCH/activity_main.py
   grep -n 'OFFER_CLASSIFIER\|"active":\|"activating":' $SCRATCH/activity_main.py
     181:OFFER_CLASSIFIER: SectionClassifier = SectionClassifier.from_groups(
     185:        "active": {
     209:        "activating": {
     230:)
   ```
   No git mutation of any kind was performed. No `add`/`commit`/`branch`/
   `checkout`/`stash`/`push`.

3. **Enumerate the 27 by AST, not by eye.** Parsed `activity_main.py` with
   `ast.parse`, located the `OFFER_CLASSIFIER` `AnnAssign`, `literal_eval`'d the
   `groups=` keyword, and took `active ∪ activating` lower-cased.
   → `ACTIVE n=22`, `ACTIVATING n=5`, union **27**.

4. **Locate and GET the object.** Bucket/prefix/key derived from
   `settings.py:427` + `storage_namespace.py:284` + `section_persistence.py:375`,
   then confirmed against a LIST before reading:
   ```
   aws s3 ls s3://autom8-s3/dataframes/1143843662099250/ --recursive | grep -i manifest
     …/manifest.json                    (legacy, entity-agnostic)
     …/offer/manifest.json              <- the offers manifest (this census)
     …/offer/manifest.json.bak-2026-07-27
     …/project/manifest.json
     …/section/manifest.json
   date -u   -> NOW_UTC=2026-08-12T20:54:08Z
   aws s3api get-object --bucket autom8-s3 \
     --key "dataframes/1143843662099250/offer/manifest.json" offer_manifest.json
   date -u   -> AFTER_GET_UTC=2026-08-12T20:54:10Z
   ```
   The `offer/` key is the write target for `entity_type="offer"`
   (`section_persistence.py:486` writes via `_make_manifest_key(project_gid,
   manifest.entity_type)`), and `OFFER_CLASSIFIER.entity_type == "offer"`
   (`activity.py:182`). The GET returned `entity_type: "offer"`, confirming the
   selection from the object itself rather than by inference.

5. **Evaluate the three criteria** by joining the 27 lower-cased classifier names
   against `{name.lower(): SectionInfo}` from the manifest; count unresolved;
   count null `last_verified_at`; compute `NOW − min(last_verified_at)` with
   `NOW` pinned to the step-4 value.

6. **Bound criterion 3 rather than assert it from one sample.**
   ```
   aws s3api list-object-versions --bucket autom8-s3 \
     --prefix "dataframes/1143843662099250/offer/manifest.json" \
     --query 'Versions[?LastModified>=`2026-08-12T04:00:00Z`].{T:LastModified,V:VersionId}' \
     --output text | sort -r     -> 42 versions
   # then one get-object --version-id per row
   ```
   Re-ran the step-5 evaluation on each of the 42, plus three coarser historical
   versions (`yWEJ5C.ucXMa4bwFgsXw44Kk5gPZVPtr` 2026-08-11T22:05:06Z,
   `oU.vP7meVcJcKWyY0kWuKTihHQP8RetZ` 2026-08-10T12:20:29Z,
   `0pGdo4NkMFgb63CreIWdjnNksmy15ac3` 2026-08-08T16:01:04Z). 45 versions total.

7. **Answer B3-b** from the same objects — count `SectionInfo.name` nulls and
   check for duplicate lower-cased names.

**Mutation audit.** Every AWS call was `sts get-caller-identity`, `s3 ls`,
`s3api list-object-versions`, or `s3api get-object`. No PUT, no DELETE, no
`lambda invoke`, no `terraform` of any kind, no Asana call of any class, no
CloudWatch alarm change. `autom8y-asr-verdicts` was neither read nor listed.
All downloaded objects were written to the session scratchpad, never into the
repo. This document is the only file written.

---

## 6. What I could not determine

Named gaps. An honest INCONCLUSIVE on a sub-question beats folding it into the PASS.

1. **Whether the classifier matches *live Asana*, as opposed to the manifest.**
   I measured classifier-vs-manifest, which is what criterion 1 asks and what
   R-O8's trigger names. I did **not** call the Asana API. Because the manifest's
   `name` is only refreshed on refetch or when null (`progressive.py:505`,
   `section_persistence.py:206,214`), a same-GID rename in Asana could sit
   invisible to this census for as long as that section goes unrefetched. The
   34↔34 bijection makes this unlikely but does not exclude it. **I could not
   verify the live Asana section vocabulary.**

2. **Which of the three skip branches produced the three partial-stamp-pass
   versions in §2.** The signature is consistent with `PROBE_FAILED`
   (`progressive.py:515-516`), Decision-5c unapplied-delta (`:517-519`), or the
   P3 null-watermark heal-and-`continue` (`:561-572`). Distinguishing them needs the
   `section_last_verified_stamped` / warm-path log lines, which I did not read.
   **I could not verify the mechanism.**

3. **Whether the 2.43 h window maximum is the true worst case.** My sweep covers
   2026-08-12T04:00Z → 20:33Z at full version resolution plus three spot samples
   back to 2026-08-08. A longer or differently-phased window (a weekend, a deploy
   freeze, an incident) could contain a larger stamp-advance gap. **I could not
   verify behaviour outside the sampled window**, and criterion 3 is a
   cadence-relative criterion, so this is a real bound on the claim's reach.

4. **Not a gap, but flagged so it is not silently absorbed — a population
   mismatch between the criteria and the currently-shipped reducer.** The B3-a
   criteria are stated against `sections_for(ACTIVE, ACTIVATING)` = **27**. The
   reducer live at `origin/main`, `metrics/freshness.py:785`, joins on
   `classifier.active_sections()` — which is `sections_for(ACTIVE)` only = **22**
   (`activity.py:88-90`), excluding the 5 `activating` names and, within them, 2
   of the 19 zero-row sections. That is the ADR-006 scoping that P-5 supersedes,
   and closing it is K-lane build work under R-alt's "attempt all-classified
   first" discipline. **I measured the 27 the criteria name, not the 22 the code
   currently joins.** I take no view on the fix; I report the delta so that a
   later seat citing "the census passed" cannot be read as "the shipped reducer
   already uses the P-5 denominator." It does not.

---

## 7. Grade

**MODERATE**, with the ceiling stated rather than implied.

**What earns the grade.** Every claim here rests on a direct present-tense probe
of an external primitive, not on a reading of code that describes the primitive.
The three criteria were evaluated by machine against 45 distinct S3 object
versions, with the classifier enumeration taken by AST from `git show
origin/main:` rather than transcribed. Command strings, VersionIds, ETags and
verbatim timestamps are recorded throughout, so a distrusting reader can re-run
step-for-step and falsify me in minutes. `now` is pinned to a receipted `date -u`
rather than left as "recent". Rite-disjointness holds: the initiative's owner rite
is 10x-dev; this seat is eunomia and designed none of what it checked (Axiom 1,
`external-critique-gate-cross-rite-residency`).

**What caps it below STRONG.**

- **Single stream.** `cross_stream_concurrence.stream_count = 1`. No second,
  independent seat confirmed these readings. The mechanical reproducibility of
  §5 is a substitute for concurrence, not an equal of it.
- **Proxy on the R-O8 answer.** §4's "no drift" is measured against the manifest,
  which is a cache of Asana, not Asana (§6 item 1). The strongest form of that
  claim is not available from the object I was scoped to read.
- **Window-bounded on criterion 3.** The criterion is cadence-relative; my bound
  is 16.9 h at full resolution and 4 days at spot resolution (§6 item 3).
- **One-directional on mechanism.** The partial-stamp-pass in §2 is observed but
  unattributed (§6 item 2).

**What is NOT a cap.** The criterion-1, criterion-2 and B3-b results are
categorical zero-failure counts over 45 versions, with the independent 19-zero-row
cross-check landing exactly on `ADR-007:1141`'s figure. I would stake the PASS on
those three. The MODERATE ceiling is carried by the R-O8 sub-answer and the
criterion-3 window, which are the two places where the evidence is inferential at
the edges.

**Routing.** No producer defect detected; nothing to route as a blocker. R-O8's
revisit trigger has fired with the answer **"all 27 resolve; zero drift; no name
to report"** — the operator's hold at
`RULING-operator-adr007-ratification-2026-08-12.md:25` can be adjudicated on this
result. K-0a is satisfied on its stated criteria; K-1's remaining gates
(K-0b ratification, K-0c contract landing) are not this seat's to assess and were
not assessed.
