# Release-Executor Memory

## Key Patterns

- `.sos/wip/` files require YAML frontmatter: `---\ntype: audit\n---` at the top.
  Execution ledgers use `type: audit`. Both .yaml and .md artifacts need this block.
  The Write hook enforces this and will flag files missing frontmatter.

## Artifact Locations

- All release artifacts written to `.sos/wip/release/`
- Inputs: `platform-state-map.yaml` (PATCH), `release-plan.yaml` + `dependency-graph.yaml` (RELEASE/PLATFORM)
- Outputs: `execution-ledger.yaml` + `execution-ledger.md`

## Container Distribution + push_only

- `distribution_type: container` with `action: push_only` does NOT trigger the container escalation rule.
  The escalation rule only applies to `publish` actions. Push-only just pushes commits; CI handles the container build.

## Dependabot Advisories on Push

- GitHub may report pre-existing Dependabot vulnerabilities in push output. These are informational,
  not push failures. Log them in `output_summary` with a note that they are pre-existing.
