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
- **The names agree (D9):** the clinic part of the PLAY title, the parent Business task's name and the name you pass to step 1 must be the same. Step 1 forgives only invisible differences (extra spaces, zero-width characters). It stops on any visible one: case, spelling ("Centre" vs "Center"), or a suffix such as "— Downtown". The deck uses the Business name.
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
- **Step 1 then renders the staged deck in a headless browser** and checks what a client would see: exactly this clinic's forwarding address, the confirmed name after "Prepared for", and no unfilled field. It refuses if no browser is found, and prints a `[render]` line naming the browser it used.
- **Step 2 checks everything in `public/` before it calls wrangler**, because wrangler publishes the whole folder. It refuses, and nothing is published, unless all of these hold:
  - `public/` holds only `_headers` and slug folders, each with just an `index.html`; `_headers` is unchanged; and every live deck in the deck-host ledger (`config/deck-manifest.json`) is still there.
  - Each slug folder is accounted for. A deck step 1 just produced (not yet deployed) is rendered again in the headless browser. A live deck (in the ledger, or marked done in `AUTOM8_FLOODGATES_STATE_DIR` and not yet in the ledger) must still match the bytes recorded for it. It is not rendered.
  - Any other folder refuses: no run state and no ledger entry (`unaccounted_slug`), a live deck edited after delivery (`deployed_sha_drift`), or a deck revoked in the ledger (`revoked_slug_present`).

  When nothing new was produced, step 2 still runs. It prints `no newly produced deck; redeploying the verified live set` and publishes the same live decks (for example, after a `_headers` change). It also refuses if wrangler's project-local cache names any Cloudflare account other than `DECK_HOST_CF_ACCOUNT_ID`.
- **Step 3** prints exactly what step 4 will post. Read it before step 4.
- **Step 4** exits non-zero if no contact card was posted. A re-run, or a run on an office that is already done, skips comments that are already there and exits 0.

## Afterwards

Add the new slug to the deck-host ledger (`config/deck-manifest.json`) and commit it there.
The entry must carry `frozen_sha256` (the sha256 printed by step 1 and stored in the run state): step 2
verifies every live deck against that field and refuses with `ledger_sha_missing` when it is absent.
Copy the entry shape from the previous entry.

## If something fails

| Symptom | Fix |
|---|---|
| `D9: name mismatch …` or `D9: … has no Business parent` | The title, the Business name and the name you passed disagree, or the PLAY has no parent Business. On a mismatch the `[failed]` line prints all three names. Fix the Asana record or pass the matching name. If you can't tell which name is right, ask the operator; don't work around it. A re-run of an office that was already produced is checked against the name it was built with. |
| `REFUSED` from the produce pre-flight | The deploy folder isn't clean. Point `DECK_HOST_DIR` at the deck-host checkout and check its `public/` holds only `_headers` and slug folders. |
| `[browser_unavailable]` or `[browser_override_invalid]` (`BrowserUnavailable`) | No Chrome, Chromium or headless shell found. Stop and ask the operator; never download one. |
| Any other `[<reason>]` from the render check (`RenderCheckRefused`) | The staged deck failed the rendered check; the reason code is in the message. On a first produce the staged folder was removed: fix the cause and run step 1 again. On an office that was already produced, nothing was removed (the deck may be live) and no deploy command was printed; ask the operator. |
| `already produced … does not exist` | An earlier produce used a different folder. Re-run with that folder, or copy its slug folder over. |
| Wrong clinic name after step 1 | Before step 2 only: remove BOTH that office's state file in `AUTOM8_FLOODGATES_STATE_DIR` and its new slug folder in `public/`, then run step 1 again. If you remove only the state file, step 2 refuses the leftover folder (`unaccounted_slug`). If you remove only the folder, step 1 stops with `already produced … does not exist`. |
| `REFUSED` from step 2 with `deploy_root_refused` | `public/` has a stray file or folder, `_headers` was changed, the ledger is missing, or a live ledger deck is missing from `public/`. The message names the cause. Fix the deck-host checkout; never delete a live deck's folder to get past it. |
| `REFUSED` from step 2 with `<slug>: <reason>` | Each refused slug folder is listed with its reason. `unaccounted_slug`: a folder with no run state and no ledger entry; if it is a leftover of a removed run, remove it. `deployed_sha_drift` or `ledger_state_disagree`: a live deck's bytes no longer match its record; ask the operator, don't edit the record. `staged_sha_drift` or a render reason: see the render check row above. |
| Cloudflare `Authentication error` | Wrong account or an expired login. Run `wrangler whoami` with `CLOUDFLARE_API_TOKEN` unset. |
| `[INCOMPLETE] … no contact card` | The Business has no usable contact. Add one in Asana, then re-run step 4. |

## Known gaps

- A run on an office that was marked done before this tooling existed, with no contact card, is not flagged.
- Nothing starts this automatically when a card is created; an operator runs the steps.
