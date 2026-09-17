---
type: decision
artifact_kind: operator-slate
initiative: read-the-name
sprint: S1.6 (soak, day 1 closed)
rite: sre
station: calendar-integration-locus
created: 2026-09-16
status: recorded
supersedes: "the §3 word-list of RULING-pythia-read-the-name-grant-adjudication-2026-09-15.md, which this dates forward"
arming_state: NOT ARMED
evidence_grade: MODERATE
refs_read: autom8y-asana origin/main 19dab888 · autom8y origin/main c95c59bb
---

# SLATE — the operator's open words, dated 2026-09-16T00:45Z

**This slate decides nothing.** It carries forward pythia's §3 list with the night's measurements
folded in, marks two words discharged **by evidence rather than by assertion**, and adds five items
the evening produced. Every item is phrased to be answerable in one line. Nothing here is authority,
and no item may be treated as settled by a relay in either direction.

---

## §1 The arming gate — unchanged, and still the only thing that blocks the arm

**W-1**, verbatim from the ruling, in this seat's own room:

> *"For the 09-22 arm: the reader of S-1 pages on `autom8y-platform-alerts` is ___; the smoke-lead
> convention from then on is ___; disarm to scratch on a misfire is pre-authorised: yes/no."*

Three blanks, and all three are still open. Without them S1.7 does its scratch-topic half and ends
**REFUSED-CORRECTLY**. The re-point itself is class **(C)** in the ruling — a specific word the
standing grant does not supply.

One fact for the first blank, measured 2026-09-15: **the guid8 → clinic lookup exists and works**
(7 of 7 named offices resolve to exactly one name over 30 days), **but it requires AWS read on
`/aws/lambda/autom8-email-booking-intake`, which today means the operator.** A named reader without
that access can be paged but cannot resolve the code on the page. That is a property of the choice,
not an objection to it.


**Added 2026-09-16T17:50Z, bearing on the first blank and on what the page means.** The founding office
`ccb52f4c` — the office this wave's north was written around — is confirmed a **relay sink**: two seats,
two keys, reconciled to the digit; **130 of 130 of its arrivals in 72 h are `unknown_loud`**, mail the
classifier could not recognise as any intake shape, arrived by relay from ~25 senders. Its RATE-floor
reading (21 of 40 runs, 1–4 %) is *native bookings ÷ a forwarded inbox* — entirely a plumbing shape. The
floor is not miscomputed; U-3 counts what it was ruled to count. The reader brief's line for this office
is rewritten (arming receipt **E-6**). Whoever is named in the first blank should know the page's founding
example does not describe a clinic.

> **The word, post-arm (F-D, same shape as F-C):** *"Exclude `unknown_loud` parks from the arrival unit
> U-3 — yes / no / only ___."* This is a pinned-query change and resets the soak by construction, so it is
> asked for **after** the arm, not during the soak. **The meaning of a running instrument can be corrected
> on the receipt; its definition cannot be corrected while it runs.**
---

## §2 NEW — the arm date is no longer 2026-09-22, and the choice is yours

Soak row 1 (2026-09-15) **passes seven of eight §3 criteria and fails the `***` attribution residual**:
day max 0.1141 against a 10 % bar, `residual_share_high: true` on 4 of 24 run lines. §3 requires
*seven **consecutive** complete rows*, so on the plain reading consecutiveness breaks.

The cause is upstream and dated: a burst in the 19:00Z hour of 09-15 (110 office-bearing lines, **65
unattributable**, 40 × `WebhookValidationError` at `stage=parse`), which sits in the 3-day rolling
window until ≈ 2026-09-18T19:00Z.

Reconstructing the criterion across 30 days: **25 of 31 days would have passed, 6 breached, and the
longest actual consecutive pass run is 15 days (08-27 … 09-10).** A clean seven-row soak has happened
twice inside the last month. **The arm needs seven days without a burst, not the upstream defect
gone** — a probability over a date, not a wall.

> **The word:** *"On the residual breach — (a) wait for seven consecutive clean rows; or (b) a
> breached row annotates rather than resets, and the arm holds its date; or (c) ___."*

**CORRECTED 2026-09-16T16:15Z, AND CORRECTED AGAIN 16:40Z — the date stands after all; what was wrong
was this seat's second reading, not its first.** At 16:15Z this entry withdrew "≈ 09-25" and wrote *"the
soak is inside a multi-day run"*, on a reading that the residual's monotonic climb through day 2 (0.1136
→ 0.1390, high on 16 of 16 runs) was fed by a fresh no-body batch of 14 at 15Z. The EBI lane stopped it,
and splitting the `***` lines by `(stage, error_type)` per hour over 36 h shows they were right:

```
no-body (parse/WebhookValidationError), *** lines per hour:
  09-15 19Z  28    20Z  8    21Z  4
  09-16 00Z   4    03Z  4    06Z  4    09Z  4    12Z  4    15Z  4        total 64
```

**One batch, on SendGrid's redelivery schedule — deterministic failure, new trace id each pass — and
nothing new has entered the class since 19Z on 09-15.** The "14 at 15Z" was 4 retries + 2
`OfficeResolutionError` + their 8 paired fault/decline lines, an hourly `***` count mistaken for a
fresh arrival. The day-2 climb is **window arithmetic**: the 19Z burst and its flat tail accumulate
inside the 3-day window while the quieter hours before it age out. **The no-body batch ages out ≈
2026-09-18T19:00Z as first dated**, and option (a)'s earliest close remains **≈ 09-25**, *if no new batch
lands* — a probability over a date, exactly as §2 already says. The small steady second feeder is
`OfficeResolutionError` (15 `***` lines in 36 h), not anything new.

One claim from the correcting lane does **not** hold on this plane and is recorded so it is not carried
by inheritance: that `FieldExtractionError` feeds the residual. It feeds **zero** `***` lines in 36 h —
those failures occur after office resolution and carry a guid, so they are attributed. Their split was of
*all* stage exceptions (190 in 36 h); this seat's residual is of *unattributable* lines (64 + 15). Two
instruments, two populations, and each of us read one as the other for an hour. Same family as every
other error tonight.

**Added 2026-09-16T22:55Z — the fork now has a concrete, dated cause, and it changes the arithmetic of (a).**
The EBI change set (autom8y #2324, bound to land ≤ 09-19) carries the no-body parse fix live at the apply,
outside any lever. **`booking_intake_fault` is a member of the S-1 arrival unit** (`query.py:67-74`), and the
handler logs it on every non-200 invocation — so a failing mail is counted **once per SendGrid redelivery**.
The fix turns that retry chain into one parked 200. **Independently re-derived on this seat's plane** (current
3-day window, the pinned query's population, the 72 no-body traces' 144 lines removed, all `***`):

> **⛔ FALSIFIED 2026-09-17T04:25Z — DO NOT ACT ON THE TABLE BELOW.** It is kept for the record, not as a
> live figure. The deploy landed and removed **none** of those lines; measured either side of the boundary,
> `***` lines per no-body trace went **2.00 → 3.00**, so the deploy made the residual **worse** per arrival,
> not 59 % better. **The sign is wrong, not just the size.** The full correction is in the OVERTAKEN block
> below, and the measurement is SOAK §3e / §3e-i.

```
TODAY                      lines 1676   *** 231   share 13.78%   -> residual tripwire HIGH   [FALSIFIED]
WITHOUT the no-body ladder lines 1532   ***  87   share  5.68%   -> residual tripwire off    [FALSIFIED]
```

The EBI lane's own analysis read 13.86% → ~6%; the two agree. **At the apply, the residual criterion that has
breached since 09-15 stops breaching.**

**This seat's ruling on its own instrument (made, not deferred):** the change is **acceptable as measurement
and truer** — it removes the retry over-count this slate's SOAK §3b names. It **does not violate the rule that
keeps §3b unapplied**: §3b would re-grade *recorded* rows leniently; the deploy changes *future traffic*, so rows
1–2 stay breached as recorded and the criterion stays exactly as strict. Two binding conditions: every row
spanning the apply records the population change on its face; and **the post-apply "off" is never recorded as
§3b vindicated or as the old criterion passing** — 13.78 % and ~5.7 % measure different populations.

**What stays the operator's, and is now sharper:** whether rows spanning that population change count as
*consecutive*. Under **(a)** the clock restarts at the apply on the new definition — and because the residual
clears at source rather than waiting on an unpredictable next batch, a clean run could start at the apply. Under
**(b)** the breached rows annotate and the date holds.

> **HELD 2026-09-16T23:0xZ — #2324 will not land this wave, and the date above is withdrawn.** The operator
> held the change set on the design of its LLM-failure narrowing: it parks on any HTTP 400, and the provider
> returns 400 when an organisation hits a self-set spend limit, so a hit limit would have **parked the fleet's
> inbound** instead of retrying it. Redesign with provider redundancy before anything lands. **So nothing in
> this wave moves the arrival unit, and the residual keeps breaching on the same redelivery over-count.** The
> ruling above stands for whenever #2324 does land. **Option (a) returns to this morning's arithmetic:** the
> 09-15 no-body batch ages out of the window on its own at ≈ 09-18T19:00Z, and a clean seven-row run closes
> ≈ 09-25 *if no new batch lands* — a probability over a date, as before. "The deploy makes (a) more
> attractive" is **not** true this wave and is struck.

**★ DATE CORRECTION 2026-09-17T05:50Z — ≈ 09-18T19:00Z IS THE WRONG CLOCK, and the right one is later.**
Two different clocks were conflated above:

1. **SendGrid's 72-hour retry ladder** would have ended ≈ 09-18T19:00Z, 72 h after the batch's first delivery.
2. **The residual's own W = 3 d rolling window** clears a line **three days after that line was WRITTEN**.

**The ladder in fact stopped EARLY — at 03:38:31Z on 09-17, about 39 h before its 72 h would have expired —
because the deploy made the endpoint answer 200 instead of 502** (SOAK §3e-i). That is the good news. **But the
lines it already wrote stay in the window until 2026-09-20T03:38Z**, which is **≈ 33 h LATER than the date
above.** Stopping the ladder early does not remove what it already wrote.

```
last no-body line measured      2026-09-17 03:38:31Z
W = 3 d rolling -> clears at    2026-09-20 03:38Z      (the slate above said ≈ 09-18 19:00Z)
first possible fully-clean day  >= 2026-09-21
seven consecutive clean rows    close no earlier than ≈ 2026-09-27, not ≈ 09-25
```

**Corroborated by the instrument's own published number rather than by this arithmetic alone: `residual_share`
is still RISING** — 13.72 % at 00:27Z to **14.53 % at 05:27Z**, `residual_share_high = 1` on every run, against
a 10 % threshold. **It is rising while NO new no-body lines are arriving**, because quieter hours age out of the
rolling window while the ladder's lines remain, and because §3e measured that the deploy made those lines
**denser** — 3.00 per trace instead of 2.00. **Row 3 will breach.**

**Shape of the class, checked before this was written so §3b is not misquoted.** No-body lines per day over
6 d: 09-11 **16** · 09-15 **40** · 09-16 **32** · 09-17 **8**, and nothing on 09-12–14. **Two separate episodes,
and §3b's "one batch on a 3-hourly ladder" correctly describes the 09-15 one**, which is the one still in the
window. The 09-11 episode has already aged out.

**★ READ THIS BEFORE THE TRIPWIRE FIRES, not after — the coming breach will LOOK like the fix having
failed, and it is not.** Put here at the EBI client lane's request, because an alarm at 08:00Z read without
this page in front of it will reach for the most recent change, and the most recent change is the fix that
**stopped** the thing being counted.

**The mechanism, corrected from the one first offered and measured here rather than reasoned.** The
neighbouring lane's version was *"the numerator is frozen and the denominator is moving."* **Historically that
is not what happened** — over the last 18 h the numerator ROSE, 193 → 212 → 231 → 243 → 255, faster than the
denominator's 1402 → 1745. The share rose because **the rolling window slid ONTO the ladder episode** while
the quiet pre-ladder days of 09-12 to 09-14 dropped out of it. **Nothing new was arriving; the window was
moving over what had already arrived.**

**What IS true, and it is true from now rather than historically:**

```
since 03:38:40Z : office-bearing lines 15 , across 5 distinct offices , of which *** = 0
                  -> the window is LIVE, so the zero is TAKEN, not untaken
```

**The numerator is frozen AS OF NOW. The denominator is live.** So:

> **PREDICTION, falsifiable at the next hourly run: `residual_share` must FALL from its 14.53 % at 05:27Z.
> If the next runs keep RISING, a feeder exists that this read did not find, and this whole explanation is
> WRONG.** It is recorded that way on purpose — the operator should be able to catch this seat out with one
> glance at the next digest.

**And the breach still happens regardless**, because the ladder's already-written lines do not leave the
W = 3 d window until **2026-09-20T03:38Z**. **A falling share and a breaching row are compatible**: the row
records the day's MAXIMUM, and the maximum for 09-17 is already above 10 %. **Row 3 will breach, and that
breach is not evidence about the fix in either direction.**

**What this does NOT say.** It bounds the **ladder's** contribution only. The residual has other feeders
(`OfficeResolutionError` and the paired lines), so **a clean row is not guaranteed even after 09-20T03:38Z** —
this moves the earliest possible date, not the expected one. **No recommendation on the fork is implied or
changed; only a date this seat had given you is corrected.**

**OVERTAKEN 2026-09-17T04:25Z — #2324 did land, and the arithmetic above is wrong in both directions.**
Read before anything else on this page, because the hold note immediately above is now false on its face.

**1. The hold was overtaken, not lifted.** #2324 was **split**: the LLM-failure narrowing the operator held it
on — park on any HTTP 400, so a provider spend-limit 400 would have parked the fleet's inbound — is **not** in
what landed. The remainder merged and deployed at **2026-09-17T01:05:49Z**, publishing **v74**. Confirmed at
the executing version rather than the deploy time: this function carries an alias, so a no-qualifier config
read attests `$LATEST` and not what served. The log-stream qualifier shows the pre-deploy lines on v73 and the
03:35–03:38Z lines on **v74**. **The operator's objection was met by removal, and this seat records that
without treating it as the operator's word on anything else.**

**2. "At the apply, the residual criterion that has breached since 09-15 stops breaching" is WITHDRAWN.**
It has not. The residual reads `chiropractor_guid`, which is still `***`; the attribution #2324 produces lands
in a different field, `office_handle`. **The criterion cannot see the fix.** Full measurement in SOAK §3e.

**3. The counterfactual table above is unrealized, and its DIRECTION is wrong.** It assumed the deploy removes
the class's 144 lines. It removes none of them. Measured on identical queries either side of the boundary:

```
v73 (pre) : 12 no-body traces -> 24 *** lines   = 2.00 *** residual lines per trace
v74 (post):  4 no-body traces -> 12 *** lines   = 3.00 *** residual lines per trace
```

The fix swapped `booking_intake_fault` for `terminal_decline` **and added `terminal_decline_parked`**, which is
a third `***` line where there were two. **Per arrival, the deploy made the residual 50 % worse, not 59 %
better.** The `13.78 % → 5.68 %` row should be read as falsified, not pending.

**4. So exactly one route to a falling residual remains, and it is not attribution.** `pipeline_completed.status`
moved **`failed` → `declined`**, which should mean SendGrid receives a terminal response and **stops the
3-hourly ladder**. Fewer traces, not fewer lines per trace, is the only mechanism left. **Dated and falsifiable:
the next ladder slot is ≈ 06:35Z on 2026-09-17.** Zero no-body traces in that hour means the class stops feeding
the residual **now** rather than at the 09-18T19:00Z age-out, with no criterion amendment at all. Four traces
means the response is still retried, and the residual is **worse** than this page records.

**5. What this does and does not do to the fork.** Rows 1–2 stay breached as recorded, under both branches —
nothing here re-grades a recorded row. Option (a)'s backstop is unchanged: the batch ages out ≈ 09-18T19:00Z
regardless. What changes is only whether it stops sooner. **This seat is not moving the fork and has no new
recommendation on it** — it is removing a false premise that was sitting under option (a), and the 06:35Z read
will be recorded here either way, including if it refutes the prediction above.
---

## §3 NEW — the silent-loss class, which outranks everything else on this page

Measured on the EBI plane and **reproduced independently here, digit for digit**: the
`WebhookValidationError` class (the webhook carries neither an html nor a text body) rejected **568
deliveries across 17 of the last 30 days**. On 120 traces sampled by the EBI lane, **every one
authenticated and reached `pipeline_completed`, and not one produced a booking, a terminal decline,
or a park.**

Mail that arrives, authenticates, and vanishes leaving no record. Each delivery carries a fresh
trace id and no message id, so **568 deliveries represent an unknown, smaller number of real
emails** — the count cannot be recovered from the plane. It is the third silent-loss class found on
that service.

> **The word (EBI's lane, his to authorise):** *"Build the missing-body parse fix — yes / no / after
> ___."* It is a new build, outside the wave already approved, and the EBI seat has correctly
> declined to start it without this.

This seat's soak row is an inconvenience with a date on it. This is not.

---

## §4 Words carried forward, unchanged

| word | the question, in one line |
|---|---|
| **W-2** | *"Extend this grant to EBI `services/email-booking-intake/**` merges-on-green whose apply is image-only (pending set empty), for the S-1 follow-ups after the arm — yes / no / only ___."* |
| **W-7** | *"SEV1 SMS is sandboxed: request production access / verify a destination number / record SMS as dead."* |

W-3 and W-5 belong to the EBI locus's room and are not asked here.

---

## §5 Two words DISCHARGED by measurement, shown so they can be contradicted

**W-4 — *"unmute the SEV1 deadmen the triage proves real"* — the answer is NONE of the four.**
The read-only triage (`TRIAGE-asana-muted-sev1-deadmen-2026-09-15.md`, merged `18ec8f81`) found all
four **stale by design**: every watched series stops in the same hour, 2026-09-05T06:00Z, because a
human disabled three schedules at 06:24:56–06:25:01Z the morning after CI re-enabled them. Not one
REAL OUTAGE, not one STALE DRIFT. Unmuting any of them pages a human on a live SMS topic for a state
the fleet ruled into existence. **No word is needed to unmute nothing; the word is only needed if
this reading is wrong.**

**W-6 — *"drop the asana image pin"* — already gone, on both stacks.** Verified at
autom8y `c95c59bb` with a positive control: no non-comment `image_tag =` assignment exists in either
`terraform/services/asana/environments/production.tfvars` or the EBI one, while the same pattern
finds 10 and 32 real assignments in those files respectively — so the zero is a true absence and not
a broken pattern. **Nothing to drop.**

---

## §6 NEW — three findings that need a word but are not unmutes

| id | finding | the word |
|---|---|---|
| **S-1** | **`asana-PROV-9-offer-artifact-uncovered` has never once read provable**: 804 of 804 datapoints at 0.0 across the entire life of its producer (verified here by own hands, daily min = max = 0.0 on all ten days). The alarm also **predates its own producer by 8 days 2 hours**. Invisible today only because the sweep is paused; it will page the instant anyone restarts it without understanding this. | *"Route the offer-axis provability finding to ___ / park it."* |
| **S-2** | **The `autom8y-asana-story-warm-dead` mute is undeclared in its own IaC.** `actions_enabled` is absent from `terraform/services/asana/story_warm_dead_alarm.tf` while the live alarm is `ActionsEnabled=False`. Narrower than it first looks — that tree has **no wired apply pipeline** and the live resource was never imported, so the revert would come from a human re-applying by hand, not a pipeline. It routes to live SMS. | *"Declare the mute in the HCL / retire the alarm / leave it."* |
| **S-3** | **`[DO NOT MERGE]` reads like a gate and is not one.** Three commits carry the marker on `origin/main` since 2026-08-01 — `c91189b6` (#2071), `002316ca` (#2105), `5ca5642c` (#1601) — all merged through PRs, and **no workflow in `.github/` references the marker.** The uncomfortable part: `c91189b6` ignored it and was **right** — it is the commit that cured the silent-drop class. A gate whose only violations produce good outcomes is the least likely ever to be wired. | *"Wire the marker as a required check / retire it."* Wiring it changes branch protection, so it is operator-only either way. |


### §6a AMENDED 2026-09-16T02:30Z, CORRECTED 02:45Z — the prose-gate class is real, and this seat got one instance wrong

A peer lane reported a binding: *never set `vars.A8_VERSION` below `v1.4.1-patch.2`*, because 20 of the
21 a8 tags from v1.3.4 write a credential literal their cure removed. That tag measurement is theirs and
is carried as theirs.

**This seat first wrote that the floor is "named in seven workflows and enforced in none". That is
WRONG on the path that matters, and the error is this night's own law turned on its author.** I searched
for a *version comparison*, found none, and read the absence of the mechanism I expected as the absence
of enforcement. **I asked a narrower question than the one I answered, and the narrow answer was
well-formed.**

**What is actually true, re-measured after the peer's correction:**

- **Data's cure IS enforced, by a property guard rather than a version test.**
  `satellite-receiver.yml` runs `scripts/a8-data-floor-guard.sh` in its **validate** job, **with no
  `if:` — deliberately, so the step is visible in every run** ("the script decides applicability"), and
  every other job `needs: validate`. It refuses a data deploy when the manifest actually checked out at
  the pinned ref names data's `SERVICE_CLIENT_ID`. It carries its own positive control: the same parse
  must find the key in asana's block, and fails **loudly** if it does not — a parse that finds nothing
  never certifies.
- **There is no version-floor enforcement for any NON-data service**, and the two guards on the
  service-deploy path (`service-deploy-dispatch.yml`, `service-deploy-lambda.yml`) emit `::warning::`
  and say in their own text that the deploy is not gated on them. Those are advisory and honest about it.
- **The absence of a version comparison is the design, not the gap** — and the reason is worth recording
  precisely, because one step of the peer's account does not survive checking. They said semver ranks
  `v1.4.1-patch.2` *below* `v1.4.1`, so a `pin >= floor` test would reject the only safe tag. **Under
  strict semver that is right** (a pre-release ranks below its release). **Under `sort -V` it is not** —
  measured here: `sort -V` orders `v1.3.4 < v1.4.1 < v1.4.1-patch.2`, ranking the safe tag *above*. So
  the hazard's direction depends on which comparator you reach for, which is itself the argument: **the
  property is the thing that matters (does this manifest name the key?), and any version test is a proxy
  for it.** The guard checks the thing, not the proxy.

**What survives, and it is still slate-worthy:** no version floor exists for any non-data service; two
guards are advisory and say so; and **a8 #126's merged commit body still instructs a rollback to
`v1.4.1`, with nothing marking it superseded.** The peer notes their own receipt was an instance of the
class too — they wrote "the floor is now live" when what is live is a property guard on one service's
path.

**One scheduled collision, reported by the peer and carried here because it is dated, not hypothetical:**
the guard's positive control depends on asana's environment block being non-empty, and the a8
single-writer release empties it **by design**. When that release lands the control breaks and the guard
refuses **every** data deploy — correct behaviour, and it will block. **It must be re-anchored before
that release, not after.** The peer is telling the auth lane directly; it is named here so it is not
lost between three seats.

**The class, with its instances corrected:**

| thing | reads as | is |
|---|---|---|
| `[DO NOT MERGE]` in a commit subject | a merge gate | prose; no workflow references it; three such commits are on main |
| a8 #126's commit body | a live rollback instruction | superseded, and nothing marks it so |
| `A8_VERSION` "the floor", on non-data paths | a version floor | advisory warnings that say so, plus error-string text |
| the EBI redaction alarm | armed paging coverage | `notBreaching` on an unwritten metric; un-fireable for 109 days |
| **this seat's own first reading of the a8 floor** | **a measured absence of enforcement** | **a measured absence of one mechanism, mistaken for the absence of all of them** |

> **The word, replacing S-3's:** *"Gates that are prose — wire them, or retire the wording that claims
> they bite: (a) the `[DO NOT MERGE]` marker, (b) the non-data `A8_VERSION` wording, (c) a8 #126's
> superseded rollback instruction, (d) ___."* Wiring any of them changes branch protection or a deploy
> workflow, so they are operator-only.

**Not taken by this seat.** The pin is outside this wave. The peer lane has been told, and told that
this entry exists, so neither of us assumes the other is carrying it.

---

## §8 NEW — a word this seat cannot take: TWO LANES, TWO IDENTIFIER BASES for the same offices

Added 2026-09-17T04:55Z. **This is a small word with a large failure mode, and it nearly fired tonight.**

**The facts, both verified.** This lane's governing text requires **bare `guid8`** in every artifact — arming
receipt §158, *"guid8 only. No clinic name, no phone digit, no full GUID"*, and the implementation ADR,
*"`office_name` in full on the plane and on the page; guid8 only in every `.ledge` artifact."* The EBI client
lane's own fence requires the opposite on its surfaces: **hashed handles, `sha256(guid8)[:8]`, never a bare
guid prefix.** **Both lanes are correctly following their own rule. Neither is at fault.**

**The failure mode, which is not hypothetical.** Two artifacts about **the same offices**, one in each basis,
**intersect at face value to the EMPTY SET** — and an empty intersection reads as *"no overlap, non-event,
nothing to see"*. It does not read as *"you compared two different alphabets"*. **Tonight this shape appeared
three times:** a face-value intersection of eleven bare guid8s against twelve hashed handles (escaped only by
hashing this seat's own first); a population test that returned **NONE on both declared bases** and read as
*"not a real office"* when the office was real; and a peer citing fence **"F2"** at this seat, where **F2 in
this lane's register is the CADENCE ruling** and means something else entirely. **Fence identifiers are
lane-local too.**

**Why it is not this seat's to settle.** Either resolution changes a governing rule in a lane. **Adopting
hashed handles here would move this lane's artifacts away from what its own record mandates**; asking the
other lane to publish bare guids would do the reverse to theirs. **A seat may not amend another lane's fence,
and it may not amend its own to match a peer's request.**

**The two shapes, stated without a recommendation:**

1. **One basis fleet-wide.** Simple to check, and it makes cross-lane intersection safe by default. Costs a
   rule change in whichever lane loses, and re-bases every existing artifact in that lane.
2. **Keep both bases, require every artifact to DECLARE its basis on its face.** Costs nothing already
   written; makes the hazard visible rather than absent; and leaves a face-value intersection still wrong,
   only now detectably wrong.

**What this seat HAS done in the meantime, so the word is not urgent:** every cross-lane comparison made
tonight was performed **after** converting to a single declared basis, the transform `sha256(guid8)[:8]` is
recorded in SOAK §3e with the note that **the arming receipt already stated it at E-6**, and the reader brief
now instructs a reader to ask **which field** a number was counted on before acting.

**The residual risk if no word is given:** a future seat intersects two lanes' artifacts at face value, gets
the empty set, and records a non-event. **That is the shape that clears a merge.**


## §7 One item this seat is NOT taking, recorded so it is not lost

The EBI lane's redaction alarm is **armed, paging to live SMS, and structurally incapable of
firing**: it reads a metric nothing writes with `treat_missing_data = notBreaching`, and its state
has not moved in **109 days**. The re-point and the missing-data treatment must be decided **in the
same change** — once the alarm reads a live metric, `notBreaching` still converts a stopped writer
into permanent silence. **That card belongs to the EBI locus and is being carried there**, named here
only so it is not mistaken for something this seat is holding.
