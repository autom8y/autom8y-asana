---
domain: release/platform-profile
generated_at: "2026-03-03T19:01:00Z"
expires_after: "30d"
source_scope:
  - "./.know/release/"
generator: cartographer
source_hash: "394d61c"
confidence: 0.85
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Platform Profile: autom8y-asana

## Repository

- **Ecosystem**: python_uv (pyproject.toml, uv.lock)
- **Version**: 1.0.0
- **Distribution**: container (Docker + ECS, not registry publish)
- **Has dependents**: false
- **Justfile**: exists (26 targets)
- **Visibility**: public

## Pipeline Chain (depth 3)

```
test.yml (on push to main)
  └─ uses: autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@main
       ├─ Lint & Type Check (ruff, mypy, semgrep)
       ├─ Test (pytest, coverage ≥80%, parallel via xdist)
       └─ Integration Tests (on push only)

satellite-dispatch.yml (on workflow_run: Test success)
  └─ GitHub App token (autom8y-satellite-dispatcher, App ID: 2500257)
  └─ repository_dispatch → autom8y/autom8y (event: satellite-deploy)

satellite-receiver.yml (autom8y/autom8y, on repository_dispatch)
  ├─ Validate Payload
  ├─ Checkout Satellite Code
  ├─ Build Service (Docker + Trivy + SBOM attestation)
  ├─ Deploy Lambda via Terraform
  └─ Deploy to ECS (rolling deployment + smoke test)
```

## Key Configuration

- **Reusable workflows**: autom8y/autom8y-workflows (migrated 2026-03-03, was autom8y/autom8y)
- **Org secrets**: APP_ID, APP_PRIVATE_KEY (visibility: all)
- **OIDC**: AWS IAM role `github-actions-deploy` for CodeArtifact auth
- **Pre-commit**: ruff format, ruff check, semgrep, mypy (strict on src/autom8_asana)
- **No manual dispatch** on test.yml (push-only trigger)
- **Manual dispatch available** on satellite-dispatch.yml (escape hatch)

## Known Flakiness

- **Sigstore attestation** (actions/attest-sbom in satellite-receiver.yml): Transient 401s observed (1 in 4 runs on 2026-03-03). Retry via `gh run rerun --failed` resolves. SRE-scope concern if frequency increases.

## Release Action

For this container-based deployment, the release action is:
1. `git push origin main` (triggers test.yml automatically)
2. On CI pass → satellite-dispatch fires automatically
3. On dispatch → satellite-receiver builds and deploys to ECS
No version bumping, tagging, or registry publish needed.
