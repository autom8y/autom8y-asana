---
type: spec
status: superseded
superseded_by: rep-onboarding-deck-email-template-v2-2026-07-07.md
artifact_class: rep-outbound-template
initiative: client-onboarding-delivery (WS-LINK arm-3 substrate)
date: 2026-07-06
purpose: >
  A fill-in outbound email a rep sends to hand a clinic its hosted onboarding-deck LINK.
  Minimal rep effort (5 slots); ZERO inference about the receiving individual — the rep
  determines the recipient from their own account-contact knowledge. Carrier-safety baked in.
---

> ## ⛔ SUPERSEDED — 2026-07-07
> This template is **superseded by
> [`rep-onboarding-deck-email-template-v2-2026-07-07.md`](rep-onboarding-deck-email-template-v2-2026-07-07.md)**.
> The P-NOVA operator ruling (ADR-contact-synthesis-card-on-play-2026-07-07) established
> that the assigned rep is **NOT** the sender: the sender is a constant
> (**Nova / support@contenteapp.com / Intercom**, human sign-in, manual sends). v1's
> `[SEND FROM]` rule ("send from the address the clinic recognizes") is FALSIFIED. Use v2.
> New offices receive v2-language template comments going forward. Do not follow the
> `[SEND FROM]`/`[REP-NAME]` bracket instructions below.

# Rep outbound: "Here's your setup walkthrough" — fill 5 brackets, send (~30s)

> **Where the link comes from:** the clinic's **Calendar Integration play** in Asana carries the
> hosted deck URL (once the link-onto-play automation lands; until then, copy it from the deploy
> receipt). One clinic = one link. Never reuse another clinic's link.

## Fill these (the only rep effort)
- `[RECIPIENT]` — the person's name **you** choose to send to. *The template makes no guess about who
  this is or their role — that's your account-contact call.*
- `[CLINIC]` — the clinic / business name (matches the name on the deck's cover — verify it).
- `[DECK LINK]` — the hosted URL from **this clinic's** Calendar Integration play
  (`https://decks.cntently.com/<slug>/`).
- `[REP NAME]` — your sign-off.
- `[SEND FROM]` — send from the address the clinic already recognizes (not a system address).

## The email (copy, fill the brackets, send)

> **Subject:** Your [CLINIC] booking setup — a quick 5-minute walkthrough

> Hi [RECIPIENT],
>
> Thanks for getting [CLINIC] started. To bring your calendar integration live, here's a short
> personalized walkthrough — about five minutes, no technical setup on your end:
>
> → **[DECK LINK]**
>
> It covers the one forwarding step that connects your inbound leads to your calendar. Once that's
> set, new booking requests flow straight into your scheduling, and we'll confirm it's live with a
> test booking.
>
> Any questions, just reply here.
>
> Best,
> [REP NAME]

## Before you hit send — 20-second check
- ☐ The link **opens to [CLINIC]'s** guide (open it once; check the clinic name on the cover).
- ☐ It's a **link, not an attachment**.
- ☐ **Nothing in your email mentions an `@appointments.contenteapp.com` address.** The guide teaches
  that forwarding step *inside* — it must never appear in the carrier email (that would defeat the
  privacy fix and confuse the client).
- ☐ Sending **from the address [CLINIC] knows** (so it doesn't look like spam).
- ☐ Recipient is the person **you** determined — the template didn't pick one.

## Why these rules (the *why* behind the *what*)
- **Link, not attachment** — attachments trip B2B spam filters and render poorly on mobile; the hosted
  link is clean, updatable, and byte-proven correct.
- **No recipient inference** — you hold the relationship and know who signs / who acts at the clinic;
  the system deliberately doesn't guess a name or role.
- **No `@appointments…` in the email** — the mailbox belongs in the guide (where the client sets up
  forwarding), never in the outreach; keeping it out of the carrier is the privacy guarantee.
