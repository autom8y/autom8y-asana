# INTEROP RECORD — `POST /calendar/reviewwave`: the external custom-booking boundary

- **status:** RECORD OF UNDERSTANDING. Not a decision, not a design, not an authorization. It exists because a critical interop between systems we control and one we do not was **undocumented**, and a reader of our repos would reasonably conclude the handler was lost rather than foreign.
- **instant:** 2026-09-08 · **repo:** `autom8y-asana` (`.ledge/decisions/` verified **not** gitignored → git-persistent)
- **authority:** operator-stated, this session, and marked as such throughout. Code anchors are own-hands at the paths given.
- **self-cap: MODERATE.** No external-side artifact was read; none is available to us.

---

## §1 THE ONE-LINE ANSWER

> **`POST /calendar/reviewwave` is NOT OURS.** It is an **external endpoint** on the **Legacy Natural Health Company ("new NHC") domain**, whose **code owner is external, associated with the cofounder**. Operator, verbatim: *"we're not responsible for any of the logic it bears."* It is nonetheless **the single POST target for all of our custom booking intake**, and it **writes into our database**. It is a boundary, not a gap.

**`ReviewWave` is a LEGACY NAME — a Croft convention.** It was the **first provider** the integration was built for and **the name was never changed**. It does **not** mean the endpoint is ReviewWave-specific. Reading the name as a provider scope is the single most likely misreading of this surface, and it is why this record exists.

**Code anchor for the legacy name, own-hands** (upgrading this from operator-relayed to corroborated): `a8/autom8` `apis/asana_api/objects/custom_field/models/text/review_wave_id.py:11-14` — `ReviewWaveId(TextField)` whose `__new__` performs an explicit `FILE_NAME.replace("review_wave", "reviewwave")`. **The codebase actively normalizes its own module spelling back to the legacy Asana field name.** The legacy convention is pinned in code, not merely remembered.

---

## §2 WHAT IT DOES (operator-stated; we hold no spec)

On our behalf, on their side, it performs several booking-protocol stages:
1. **Writes the appointment to a shared Google Calendar.**
2. **Sends notifications.**
3. **Updates the lead in our database.**

There is no OpenAPI document, schema, or contract artifact on our side. **Our client code is the only expression of the contract we hold.**

---

## §3 SCOPE — what routes through it, and what emphatically does not

**Operator-ruled: ALL NON-GHL PROVIDERS route through this one endpoint.** The provider determines how a booking was **CAPTURED upstream**, never where it is **POSTED**.

Provider surface, own-hands at `a8/autom8` `apis/asana_api/objects/task/models/unit_holder/main.py` (the `UnitHolder` field map, `:79-109`):

| field | custom-field model | routes through `/calendar/reviewwave` |
|---|---|---|
| `acuity_cal_url` | `AcuityCalId` `:79` | YES |
| `calendly_url` | `CalendlyUrl` `:80` | YES |
| `sked_id` | `SkedId` `:82` | YES |
| `reviewwave_id` | `ReviewWaveId` `:84` | YES |
| `janeapp_url` | `JaneAppUrl` `:108` | YES |
| `ehr_cal_url` | `EHRCalUrl` `:109` | YES |
| Google Cal / CustomCal | `GoogleCalId`, `CustomCalStatus`, `CustomCalUrl` | YES |

### ★ §3.1 THE GHL DISTINCTION — the trap this section exists to close

Two different things share the vendor name **GHL**, and conflating them is a category error:

- **INTERNAL GHL calendars — the duration-keyed entries** (`GhlFifteen`, `GhlTwenty`, … `GhlOneHundredTwenty`, plus the `GhlTTV*` variants). These are calendars **WE create** for some clients. **They are NOT EBI. They are NOT calendar-integration. They are handled entirely separately, external to our code, and are NOT RELEVANT to these fronts.** Operator-stated. Do not import them into any calendar-integration denominator, tier split, or client-outcome bar.
- **`CustomGHLId` — the client brings THEIR OWN GHL calendar.** A different case with the same vendor name. **Whether CustomGHL routes through this endpoint is an OPEN QUESTION**, explicitly not settled when scope was ruled. Recorded as open; not assumed either way.

---

## §4 OUR SIDE OF THE BOUNDARY — anchors, own-hands, in the legacy monolith

**All of this lives in `/Users/tomtenuta/Code/a8/autom8` — the legacy monolith — NOT in the `autom8y*` tree.** A search confined to the modern repos returns a clean zero and reads as "the handler is missing." It is not missing; it is foreign, and its client is in a different repo.

- **The binding.** `sql/objects/chiropractors.py:108` — `reviewwave_id = Column(String(45), nullable=True)`, also listed at `:188`. The office↔ReviewWave binding on our side, carrying the legacy name for every provider.
- **The call chain.** `.ledge/reviews/RETRO-monmouth-lead-visibility-2026-08-19.md:32` — `ClientLead.run() → legacy POST /calendar/reviewwave`, inside a four-plane conceptualization over one shared MySQL.
- **★ The attribution gap, recorded in that same retro:** this path *"creates leads + appointments with **NO attribution**: source_id, page_id, channel, platform, hidden all empty."* Bookings that arrive this way are, by construction, unattributed at creation.

---

## §5 ★★ THE TRUST POSTURE — the load-bearing hazard

`.ledge/reviews/integration-crusade/CASE-FILE-integration-crusade.md:29`, verbatim:

> *"AXIS-2: Contente booking POST /calendar/reviewwave … PARTIAL — **2xx trust posture masks body-contract drift**; retry-exhaustion is latent, not masking."*

**Operator-ruled: a 2xx is genuinely ALL we get.** No meaningful response body, no returned identifier, no callback.

**Therefore, stated so it cannot be misread:**

> ### A 2xx from this endpoint IS NOT EVIDENCE THAT THE BOOKING LANDED.
> Any disposition, receipt, or verdict that rests on *"we got a 2xx"* is **known-unsound by our own case file.**

**This is a STRUCTURAL gap, not a fixable one.** Because the endpoint returns nothing to validate against, **verification has to be built on OUR side.** No conversation with the external owner closes it. That places it squarely inside `name-the-client`'s territory — and it is precisely why that initiative's receipt clause demands a **two-sided** reading (a failure for the same office must also name it, with its kind, never blank) rather than an acknowledgement.

---

## §6 OWNERSHIP AND ESCALATION — a person, not a process

| | |
|---|---|
| **Code owner** | **EXTERNAL** — Legacy NHC domain, associated with the cofounder. We hold no source, no repo, no deploy path, no account. |
| **Our responsibility** | The **client side only**: what we POST, and what we do with the answer. Their logic is not ours to fix, review, or certify. |
| **Escalation on contract drift** | **The cofounder, informally.** Operator-ruled. **There is no formal channel, no ticket queue, and no SLA.** |
| **Watcher** | **NO WATCHER.** |

Recorded plainly because a record naming a hazard with no remedy would be worse than none: **the escalation path for a contract drift on a production booking path is one person and a conversation.**

---

## §7 ★ CONFLATION TRAP — two Lambdas that are ours and are NOT this endpoint

Own-hands, 2026-09-08:

```
lambda-python-notify-reviewwave-booking-run-prod   State=Inactive   LastModified 2024-01-22
lambda-python-notify-reviewwave-booking-run-dev    State=Inactive   LastModified 2024-01-04
POSITIVE CONTROL: autom8-email-booking-intake      State=Active     LastModified 2026-09-05
```

A dead **notify** path, inactive ~20 months. `a8/autom8/.ledge/reviews/decommission-receipts-2026-09-04/08-dead-ingress-gate-20260906T011550Z.json` records `invocations_in_window: 0` for both (`records[59]`/`[60]`, `action: gate-check`, `mode: DRY-RUN`).

**Anyone reading "a reviewwave lambda exists" as "the receiver runs" is wrong twice: wrong service, and dead besides.**

---

## §8 A FRAMING CORRECTION OWED TO THE RECORD

`.sos/wip/CUSTODY-name-the-zero-wave2-register-2026-09-08.md:31` states the handler *"exists in NO repo on disk."* **True on the facts, misleading in framing** — it reads as a gap in our tree when the truth is **it was never ours**. A successor acting on that line will keep searching for something that cannot be found. Amend to: *externally owned; client side lives in `a8/autom8`.*

**Consequence for C-13 / R-65.** That ruling reserves *"read the receiver's handler first"* to the operator's own hand. **That act cannot mean reading code** — the code is outside every repo and account we hold. **It can only mean asking the external owner.** Which collapses it into the same conversation R-35 is already waiting on: **C-13 and R-35 are not two waits. They are one.**

---

## §9 WHAT THIS RECORD DOES NOT DO

Authorizes nothing. Decides nothing. Certifies nothing. It does **not** rule on `CustomGHLId`'s routing (§3.1, open). It does **not** dispose of the dead-letter row. It does **not** claim R-35 or any freeze reaches the external endpoint. No external-side artifact was read, because none is available to us — **every statement about what the endpoint does internally is operator-relayed, not verified**, and must not be re-cited as measurement.

**Locality caveat, recorded rather than hidden:** this record lives in `autom8y-asana` while the client code it describes lives in `a8/autom8`. **A reader debugging the POST is in the wrong repo to find this file.** If that costs someone an hour, the fix is a pointer from the monolith — not a second copy.
