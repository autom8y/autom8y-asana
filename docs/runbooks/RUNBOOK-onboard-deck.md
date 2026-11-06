# Runbook: onboarding deck for a calendar-integration client

Use this when a client activates and their `PLAY: Custom Calendar Integration — <clinic>`
task needs the Gmail Forwarding Setup deck. The run posts three comments on that task:

- the deck link
- the rep email template, with the clinic's forwarding address
- the client's contact card

Nothing is sent to the client. The rep sends the email.

## Before you start

- **The PLAY task:**
  - is in the Calendar-Integrations project, in the **ACTIVE** section
  - is named `PLAY: Custom Calendar Integration — <clinic>`
  - has a parent Business whose `Company ID` is filled in (a lowercase UUID)
- **Your shell:**
  - is in this repository, with direnv loaded (it serves `ASANA_PAT`)
  - has `AUTOM8_FLOODGATES_STATE_DIR` set to ONE absolute directory, the same one every time and from every checkout. It holds each client's run state; a second directory would mint a second deck.
  - has `DECK_HOST_DIR` set to your deck-host checkout
  - has `DECK_HOST_CF_ACCOUNT_ID` set to the Cloudflare account that owns the `deck-host` Pages project
- **Cloudflare:** a wrangler login on that account (`wrangler login`, in an interactive terminal).
- **Node:** node 22 or newer, which `mise` provides. The recipes call `mise exec node@22`.

## Steps

```sh
just onboard-deck-name <play_gid>                  # 0. print the clinic name the title suggests
just onboard-deck-produce <play_gid> "<clinic>"    # 1. build + stage the deck with the confirmed name
just onboard-deck-deploy                           # 2. publish to the deck host (production)
just onboard-deck-preview <play_gid>               # 3. re-check the live deck; print the three comments
just onboard-deck-post <play_gid>                  # 4. post the three comments on the PLAY task
```

- **Step 0 is read-only.** Check the suggested name before step 1. The name you pass to step 1 is printed in the deck ("Prepared for …") and in the rep template, and it can't be changed after step 1 without starting over.
- **Step 1 checks the deploy folder first.** It refuses before building anything if the folder would fail the deploy guard. A brand-new, empty folder is refused too, so always point it at the deck-host checkout.
- **Step 2** refuses if wrangler's project-local cache names any Cloudflare account other than `DECK_HOST_CF_ACCOUNT_ID`.
- **Step 3** prints exactly what step 4 will post. Read it before step 4.
- **Step 4** exits non-zero if no contact card was posted. A re-run, or a run on an office that is already done, skips comments that are already there and exits 0.

## Afterwards

Add the new slug to the deck-host ledger (`config/deck-manifest.json`) and commit it there.
Copy the entry shape from the previous entry.

## If something fails

| Symptom | Fix |
|---|---|
| `REFUSED` from the produce pre-flight | The deploy folder isn't clean. Point `DECK_HOST_DIR` at the deck-host checkout and check its `public/` holds only `_headers` and slug folders. |
| `already produced … does not exist` | An earlier produce used a different folder. Re-run with that folder, or copy its slug folder over. |
| Wrong clinic name after step 1 | Before step 2 only: remove that office's state file in `AUTOM8_FLOODGATES_STATE_DIR` and its new slug folder in `public/`, then run step 1 again. |
| Cloudflare `Authentication error` | Wrong account or an expired login. Run `wrangler whoami` with `CLOUDFLARE_API_TOKEN` unset. |
| `[INCOMPLETE] … no contact card` | The Business has no usable contact. Add one in Asana, then re-run step 4. |

## Known gaps

- A run on an office that was marked done before this tooling existed, with no contact card, is not flagged.
- Nothing starts this automatically when a card is created; an operator runs the steps.
