# Node >=22 deploy bundling — ADR-WALK-B2 (CON-2 / U-4 BUILD PRECONDITION)

> **Status: RESIDUAL — NOT asserted by the build session.** The A2 producer
> subprocess is mechanism-proven *offline* (Node v22.23.1 dev env; producer
> freeze GREEN + ADDR-NON-CANONICAL RED — see the spike receipt and the
> `test_onboarding_walkthrough.py::TestProducerFreezeReal` suite). Whether a
> Node >=22 runtime + the producer tree fit the Lambda/ECS **package and
> cold-start budget** is the open deploy-owner precondition. This file is the
> bundling *guidance* (ADR-WALK-B2), not a proof that it has been deployed.

The `OnboardingWalkthroughWorkflow` shells the Node >=22 producer
(`node build/inline.mjs`) as the sole deck freezer (G-PROPAGATE P2). The
runtime contract the deploy artifact must satisfy:

| Requirement | Detail |
|-------------|--------|
| Node >=22 on `PATH` | `mise` is **not** present at Lambda/ECS runtime; bundle the binary. |
| Producer tree present | `@contente/deck-inliner` (`build/inline.mjs` + `node_modules` from `npm ci`) co-located on a path. |
| Writable `export/` | The producer writes `export/<out>`; the path must be writable (`/tmp` in Lambda). |
| `AUTOM8_WALKTHROUGH_PRODUCER_DIR` | Points the workflow at the producer dir (CONFIG; never hardcoded). |
| `AUTOM8_WALKTHROUGH_ENABLED` | Kill-switch; defaults OFF (MC-2 #725 broad-rollout block). |

## Primary: container image (ADR-WALK-B2)

Add a Node stage to the existing multi-stage `Dockerfile` and copy the
producer + its `node_modules` into the final image. Illustrative fragment
(the deploy owner integrates + sizes it against the budget):

```dockerfile
# --- Node >=22 producer stage -------------------------------------------------
FROM node:22-bookworm-slim AS producer
WORKDIR /opt/contente-deck-inliner
# Source the producer from its published/pinned ref (A4 upgrade path) or vendor
# the build tree. npm ci installs the offline runtime deps (entities, parse5).
COPY deck-inliner/ ./
RUN npm ci --omit=dev

# --- final image -------------------------------------------------------------
# (in the existing final stage, after the Python layers)
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=producer /opt/contente-deck-inliner /opt/contente-deck-inliner
ENV AUTOM8_WALKTHROUGH_PRODUCER_DIR=/opt/contente-deck-inliner
# Lambda: producer writes export/ under the only writable mount.
# ENV AUTOM8_WALKTHROUGH_PRODUCER_DIR=/tmp/contente-deck-inliner  # + copy at cold start
```

## Fallbacks

- **Lambda Layer (Node >=22 binary)** — viable while the deploy stays zip-Lambda;
  constrained by the 250 MB unzipped layer budget shared with deps, and the
  producer tree still ships separately.
- **A4 publish (`@contente/deck-inliner` pinned artifact)** — the explicit
  fallback trigger: if NEITHER container NOR Layer fits the package/cold-start
  budget, publish the producer as a version-pinned dependency (mirroring
  `@autom8y/contente-tokens#v1.0.0`) and replace the worktree subprocess path.

## Verification the deploy owner MUST run (then this residual closes)

1. `node --version` inside the deployed artifact → `>= v22`.
2. From the container, run the producer GREEN + RED probes (the AC-MECHANISM
   receipt) against a writable `export/`.
3. Measure cold-start + per-task freeze latency against the NFR-5 target
   (P95 < 5 s). RED on the budget → escalate to the A4 publish fallback.

Until 1–3 pass in the deploy environment, CON-2 stays an open BUILD
PRECONDITION and the walkthrough send is gated by `AUTOM8_WALKTHROUGH_ENABLED`
(default OFF) + the user-reserved deploy/send levers.
