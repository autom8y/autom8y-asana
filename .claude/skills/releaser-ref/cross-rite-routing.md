---
name: cross-rite-routing
description: "Cross-Rite Routing Table for the releaser rite. Maps CI failure signals to peer rites (arch, sre, hygiene, review, security, debt-triage). Read when: pipeline-monitor needs to recommend routing a CI failure to a peer rite, or determining which specialist rite handles a given class of release blocker."
---

# Cross-Rite Routing Table

| Trigger Signal | Target Rite | When |
|----------------|-------------|------|
| Architectural boundary violations | arch | Repo structure suggests coupling issues |
| Deployment, scaling, infrastructure | sre | CI reveals deployment or reliability issues |
| Code quality blocking publish | hygiene | CI failures from lint/format gates |
| Systematic test failures | review | Failures suggest deeper code issues |
| Security vulnerabilities in CI | security | CI security scan failures |
| Version drift, dependency rot | debt-triage | Accumulated technical debt blocking release |

Route by reference only. Pipeline-monitor names the target rite in recommendations. User decides.
No transitive routing — releaser routes directly to peer rites, never chains.
