# Spike: Production Asana API Verification

**Date**: 2026-02-11
**Status**: COMPLETE
**Timebox**: Single session
**Informs**: Architect design decisions for resolution depth, entity modeling, and Products-driven branching

---

## Question

Three open questions from the deep spike required production data verification before the architect designs the Workflow Resolution Platform:

1. **Dependency count distribution** — What's the typical dependency count per process?
2. **DNA/Play usage frequency** — How often are BackendOnboardABusiness and other IsolatedPlay subtypes created?
3. **Products enum values** — What are the current production enum options?

---

## Approach

- Queried Asana REST API v1.0 using PAT authentication
- Test business: **Nation of Wellness** (GID: `1201774764681405`)
- Sampled 5 businesses for dependency patterns
- Sampled 10 Implementation project processes for dependency depth
- Queried custom field definitions for Products and Vertical enums
- Counted Play types in DNAHolder project (Backend Client Success DNA)

---

## Findings

### 1. Dependency Count Distribution

**Result: Dependencies are SPARSE — most processes have 0 dependencies.**

| Sample | Processes | Total Deps | Total Dependents | Avg Deps | Avg Dependents |
|--------|-----------|-----------|-----------------|----------|----------------|
| 5 businesses (early-stage) | 5 | 0 | 10 | 0.0 | 2.0 |
| 10 Implementation tasks | 10 | 2 | 4 | 0.2 | 0.4 |
| Nation of Wellness (2 processes) | 2 | 0 | 1 | 0.0 | 0.5 |

**Key observations:**
- **Template tasks** (e.g., "Implementation Process - [Business Name]") have 0 deps — they're unused templates
- **Real converted processes** have 1 dep each: always a Play (BackendOnboardABusiness)
- **Play → Implementation** is the primary dependency pattern: Play must complete before Implementation starts
- **Dependents are more common than dependencies**: processes typically have 0-2 dependents (things waiting on them)
- The spike's concern about the "40-item overflow threshold" for dependencies is moot — real-world dep counts never approach this

**Example: Nation of Wellness Play task (1204344429877768)**
- Dependencies: 0 (Play doesn't depend on anything)
- Dependents: 2 (Implementation process + Offer)

**Example: Real Implementation (Dr. Stanley Gavriel)**
- Dependencies: 1 (Play: Backend Onboard A Business)
- Dependents: 2

### 2. DNA/Play Usage Frequency

**Result: Play is the DOMINANT DNA entity type. BackendOnboardABusiness is the critical subtype.**

**DNAHolder project (Backend Client Success DNA, GID: 1167650840134033):**
- In the first 100 tasks: **93 PLAYs**, 0 REQUESTs, 7 other
- **BackendOnboardABusiness** specifically: **100+ instances found** (97 completed, 3 incomplete — capped at search limit)

**Play naming pattern in production:**
The vast majority of DNA tasks are NOT named like legacy IsolatedPlay subtypes. They fall into two categories:

1. **Structured plays** (~30%): Named `PLAY: Backend Onboard A Business (FB/IG) — {Business Name}` — these are the lifecycle-automated plays
2. **Ad-hoc plays** (~70%): Free-form descriptions of customer interactions, requests, and follow-ups — e.g., "PLAY: Client texted asking for the invoice information"

**Critical finding**: The DNAHolder is NOT just for lifecycle-related plays. It's a **general-purpose task container** for all customer success interactions. The legacy "IsolatedPlay" subtypes (PauseABusinessUnit, QuestionOnPerformance, etc.) are NOT visible as distinct types in production — they're all just tasks with different names in the same project.

**DNA custom fields actually used in production:**
- `Intercom Link` (text) — used on some tasks
- `Convo Status` (enum) — rarely populated
- `Mins Required` (number) — rarely populated
- `DNA Priority` (enum) — values: "High (Same day)", etc. — occasionally used
- `Tier Reached` (enum) — "Tier 1", "Tier 2", "Tier 3" — commonly used
- `Macro Name` (text) — rarely populated
- `Vertical` (enum) — sometimes populated (inherited from parent)
- `Products` (multi_enum) — sometimes populated (inherited from parent)
- `Automation` (enum) — "On" on automated plays
- `Status` (enum) — rarely populated

### 3. Products Enum Values

**Result: 6 active product types.**

| GID | Name | Enabled |
|-----|------|---------|
| `1202616652078540` | **Meta Marketing** | Yes |
| `1202616652078541` | **TikTok Marketing** | Yes |
| `1202616652078542` | **Newsletter Product** | Yes |
| `1208821387407275` | **Videography** | Yes |
| `1212939201474979` | **Video Session** | Yes |
| `1209078821417789` | **FB & IG Marketing** | Yes |

**Current usage on test business (Nation of Wellness Unit):**
- Products: `Meta Marketing`, `Videography`, `Video Session`

**Note**: "FB & IG Marketing" vs "Meta Marketing" appears to be a naming evolution (same platform, different label). The architect should clarify whether these represent distinct product offerings or are aliases.

---

## Bonus Findings

### Vertical Enum (Full Production Inventory)

**57 total values** (53 enabled, 4 disabled):

**Enabled verticals** (alphabetical):
8ww, acoustic_wave, acupuncture, adhd, aesthetics, allergy, arpwave, auto_injury, back_on_trac, balance, chiropractic, cupping, dentistry, functional_medicine, injury, integ_therapy, internal, invisa_red, iv_therapy, knee_pain, laser_hair, laser_therapy, marketing, massage, mens_health, motherhood, naturopathy, neurodiversity, neuro_rehab, neuropathy, nutrition, optometry, orthodontics, orthotics, pain_mgmt, partner, peptide, personal_train, phys_therapy, please-get, podiatry, psychiatry, psychology, regen_med, scoliosis, shockwave, softwave, spinal_decomp, stretch, testosterone, urgent_care, weight_loss

**Disabled verticals**: dermatology, Medical Devices, Medi Spa, Regenerative Medicine, spinal_decompression (replaced by spinal_decomp)

### Pipeline Project Section Inventory (Complete)

| Pipeline | GID | Sections |
|----------|-----|----------|
| **Sales** | `1200944186565610` | TEMPLATE, OPPORTUNITY, ACTIVE, CONVERTED, DID NOT CONVERT, COMPLETED, INACTIVE |
| **Onboarding** | `1201319387632570` | TEMPLATE, OPPORTUNITY, DELAYED, SCHEDULED, INACTIVE, ACTIVE, EXECUTING, CONVERTED, DID NOT CONVERT, TASKS, COMPLETED |
| **Implementation** | `1201476141989746` | TEMPLATE, OPPORTUNITY, VIDEO ONLY, DELAYED, CONVERTED, DID NOT CONVERT, COMPLETED, INACTIVE, EXECUTING |
| **Retention** | `1201346565918814` | TEMPLATE, OPPORTUNITY, CONVERTED, DID NOT CONVERT, FREE MONTH, SCHEDULED, INACTIVE, ACTIVE, BUILDING, COMPLETED |
| **Outreach** | `1201753128450029` | TEMPLATES, REQUESTED, OPPORTUNITY, ACTIVE, CONVERTED, MAYBE, DID NOT CONVERT, COMPLETED, UNPROCESSED |
| **Reactivation** | `1201265144487549` | TEMPLATE, OPPORTUNITY, SCHEDULED, INACTIVE, ACTIVE, CONVERTED, DID NOT CONVERT, PROCESSING, TASKS, EXECUTING, COMPLETED |
| **Expansion** | `1201265144487557` | TEMPLATE, OPPORTUNITY, INACTIVE, SCHEDULED, CONVERTED, DID NOT CONVERT, COMPLETED |
| **Account Error** | `1201684018234520` | Untitled section, TEMPLATE, OPPORTUNITY, CONTACTED, SCHEDULED, CONVERTED, DID NOT CONVERT, COMPLETED |
| **Account Setup** | `1210108583582591` | Untitled section, ACTIVE, COMPLETED |
| **Playbooks** | `1203701563408264` | Backlog, Filming Recordings, Building PLAYS, Reviewing PLAYS, Completed PLAYS, Scheduled |

**Common section pattern**: TEMPLATE → OPPORTUNITY → [stage-specific] → CONVERTED/DID NOT CONVERT → COMPLETED

**Unique patterns per stage:**
- **Onboarding/Reactivation**: Have EXECUTING + TASKS sections (multi-step work tracking)
- **Retention**: Has FREE MONTH + BUILDING (retention-specific states)
- **Outreach**: Has MAYBE + UNPROCESSED (soft outcomes)
- **Account Error**: Has CONTACTED (payment follow-up state)
- **Implementation**: Has VIDEO ONLY (content production track)
- **Playbooks**: Completely different section model (content pipeline, not lifecycle)

### Nation of Wellness Entity Hierarchy (Production Verified)

```
Business: Nation of Wellness (1201774764681405, project: Businesses)
├── ContactHolder (1201774699218198, project: Contact Holder)
├── UnitHolder (1201774699211039, project: Units)
│   └── Unit: Spinal Decompression (1205571477139891, project: Business Units)
│       ├── OfferHolder (1205571477139897, project: Offer Holders)
│       └── ProcessHolder (1205571482650638, NO project)
│           ├── Sales (1209719836385072, project: Sales, section: CONVERTED) ✓
│           └── Onboarding (1212939204328602, project: Onboarding, section: CONVERTED) ✓
├── LocationHolder (1201774764169252, NO project)
├── DNAHolder "PLAYS/REQUESTS" (1201774831052569, NO project)
│   ├── PLAY: Backend Onboard A Business (FB/IG) × 4 (all completed, various verticals)
│   ├── PLAY: Backend Onboard A Business FB/IG × 3 (completed, softwave + spinal_decomp)
│   ├── REQUEST: Unsubscribe email × 1 (completed)
│   └── REQUEST: Add/change notification email × 1 (completed)
├── ReconciliationHolder (1201774764463112, project: Reconciliations)
├── AssetEditHolder (1203421687860105, project: Asset Edit Holder)
└── VideographyHolder (1208804419439572, project: Videography Services)
```

**Key observations:**
- ProcessHolder and LocationHolder have NO project membership (confirmed from spike)
- DNAHolder has NO project membership (uses "Backend Client Success DNA" project on its children)
- Nation of Wellness has **7 Backend Onboard plays** — one per vertical/product combination across lifecycle iterations
- Both Sales and Onboarding processes are CONVERTED (healthy lifecycle progression)
- Unit has 1 Unit (Spinal Decompression) with Products: Meta Marketing + Videography + Video Session

### Business Custom Fields (21 fields on Business entity)

| Field | Type | Value (Nation of Wellness) |
|-------|------|--------------------------|
| Rep | people | Tom Tenuta |
| Company ID | text | UUID |
| Office Phone | text | +14079068111 |
| Facebook Page ID | number | 111062098766670 |
| Fallback Page ID | number | null |
| Owner Name | text | Dr. Test Tenuta |
| Owner Nickname | text | Dr. Tenuta |
| # of Reviews | number | 50 |
| Review 1 | text | (long review text) |
| Review 2 | text | (long review text) |
| Reviews Link | text | tinyurl link |
| Google Cal ID | text | (calendar ID) |
| Scheduling Link | text | null |
| Aggression Level | enum | Medium |
| Booking Type | enum | Standard |
| VCA Status | enum | Disabled |
| Twilio Phone # | text | +16893004331 |
| Stripe ID | text | cus_M6xbPyUaWAXY3Z |
| Vertical | enum | spinal_decomp |
| Stripe Link | text | Stripe dashboard URL |
| Max Pipeline Stage | number | null |

### Unit Custom Fields (Extensive — 60+ fields)

The Unit entity has significantly more custom fields than Business, including:
- **Campaign fields**: Ad Account ID, Meta Spend, TikTok Spend, Weekly Ad Spend, MRR, Radius, Min/Max Age, Gender, Languages, Currency
- **Products**: MultiEnumField (the key routing field)
- **Platforms**: MultiEnumField (meta, etc.)
- **Form Questions**: MultiEnumField with 28 question types
- **Scheduling IDs**: 14 GHL duration-based calendar IDs (10-min through 120-min)
- **Verification**: SMS Lead Verification, Work Email Verification
- **External IDs**: AA IDs, Sked ID, TrackStat ID, ReviewWave ID, etc.

---

## Impact on Architect Decisions

### 1. Dependency Strategy
- Dependencies are sparse (0-1 per process). No need for complex batching or overflow handling.
- The primary pattern is **Play → Implementation** (Play blocks Implementation).
- Hierarchy traversal is more important than dependency traversal for resolution.
- The "40-item overflow threshold" in cache settings is wildly oversized for actual usage.

### 2. DNA/Play Modeling
- DNA is a **general-purpose interaction container**, not just lifecycle automation.
- Only `BackendOnboardABusiness` needs lifecycle engine support initially.
- Other IsolatedPlay subtypes (Pause, Question, CustomCalendar, MetaAdmin) appear to be operational tasks, not lifecycle-automated.
- DNA custom fields to model: primarily `DNA Priority`, `Tier Reached`, `Automation` (enum), plus inherited `Vertical` and `Products`.

### 3. Products Routing
- 6 active products. Only **Videography** and **Video Session** trigger non-standard entity creation (SourceVideographer, Playbooks pipeline).
- "Meta Marketing" vs "FB & IG Marketing" naming overlap needs clarification.
- Products field is on **Unit** (not Business) — resolution must traverse Business → UnitHolder → Unit to read Products.

### 4. Section-Based State Machine
- CONVERTED / DID NOT CONVERT are universal across all 8 pipeline projects.
- Each pipeline has unique intermediate states (EXECUTING, CONTACTED, FREE MONTH, etc.).
- TEMPLATE sections exist in all pipelines — confirm template-based entity creation.
- COMPLETED is the terminal state in all pipelines.

### 5. Unit Is the Data-Heavy Entity
- Unit has 60+ custom fields (far more than Business's 21).
- Most campaign/targeting configuration lives on Unit, not Business.
- This means resolution from Process to campaign data requires: Process → Unit traversal (via ProcessHolder parent chain).

---

## Remaining Questions for Architect

1. Are "Meta Marketing" and "FB & IG Marketing" distinct products or aliases?
2. Should the lifecycle engine handle Playbooks pipeline (content production) or just the standard lifecycle?
3. Account Setup is a secondary project membership on Onboarding tasks — is this a parallel tracking mechanism?
4. Is "Max Pipeline Stage" (on Business) used for anything currently? It was null on the test business.
