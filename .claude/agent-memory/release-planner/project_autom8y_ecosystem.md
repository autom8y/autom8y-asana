---
name: autom8y platform ecosystem — release topology
description: Release topology for the autom8y SDK monorepo and 5 consumer satellite services, including CodeArtifact domain, satellite-deploy chain structure, and recurring escalation patterns
type: project
---

The autom8y platform consists of an SDK monorepo (`/Users/tomtenuta/Code/a8/repos/autom8y`) and 5 consumer satellite services: autom8y-asana, autom8y-ads, autom8y-data, autom8y-sms, autom8y-scheduling. All are Python/uv ecosystem.

**Why:** This context is the stable platform topology that should be assumed in all release planning for this project.

**How to apply:** Pre-populate release plans with this topology instead of re-deriving from scratch.

## SDK Publish

- Command: `just ca-publish <package-name>` run from `/Users/tomtenuta/Code/a8/repos/autom8y`
- CodeArtifact domain: `autom8y`, repository: `autom8y-python`, region: `us-east-1`, domain owner: `696318035277`
- Registry is authoritative for version status (not git tags)
- `ca-publish-all` publishes all packages; `ca-publish <name>` publishes a single package

## Consumer Satellite Deploy Chain (3-stage, per satellite)

All 5 consumers use container distribution (not registry publish):

```
Stage 1: test.yml              — push trigger on main in satellite repo
Stage 2: satellite-dispatch.yml — workflow_run trigger on test success
Stage 3: satellite-receiver.yml — repository_dispatch: satellite-deploy, runs in autom8y/autom8y
```

`satellite-receiver.yml` in `autom8y/autom8y` is the terminal stage for ALL 5 satellites — the platform's long-pole workflow.

## Recurring Escalation Patterns

- **ESC-001 pattern** (autom8y-data): path dependency on autom8y-telemetry in uv.lock. Check with `grep -A3 'name = "autom8y-telemetry"' uv.lock` before declaring CI clean.
- **ESC-003 pattern** (autom8y-scheduling): 7 pre-existing test failures. Non-blocking but must be tracked — new failures beyond 7 must be escalated.
- **SDK tag mismatch pattern**: Git tags lag behind pyproject.toml versions. Registry (CodeArtifact) is authoritative; missing tags do not block publish if the version is already in CA.

## 2026-03-25 Release State

Phase 1 published: autom8y-reconciliation 1.1.0 (was only 0.1.0 in CA).
Phase 2: All 5 satellites already pushed to main with hygiene commits; CI in-flight.
No version bumps were required for consumer satellites (all SDK constraints satisfied by already-published versions).
