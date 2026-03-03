---
name: literature-review
description: "Structured literature review protocol with evidence grading and source taxonomy. Produces evidence-graded findings compatible with .know/ output. Use when: citing external literature, grading evidence quality, structuring research findings, producing literature knowledge files. Triggers: literature review, evidence grading, research protocol, source evaluation, citation quality, external scholarship."
---

# literature-review

> Structured protocol for evidence-graded literature review. Produces findings compatible with `.know/` persistence.

## Evidence Grading Scale

Every claim extracted from literature MUST be assigned one of four evidence tiers:

| Tier | Criteria | When to Assign |
|------|----------|---------------|
| **STRONG** | 2+ independent corroborating sources from primary literature (peer-reviewed papers, RFCs, official specifications) | Claim appears in multiple authoritative sources with consistent framing |
| **MODERATE** | 1 primary source OR 2+ credible secondary sources (textbooks, official documentation, established conference talks) | Claim has authoritative backing but lacks independent corroboration |
| **WEAK** | Secondary sources only (blog posts, tutorials, informal talks) OR single non-peer-reviewed source | Claim is plausible but lacks authoritative backing |
| **UNVERIFIED** | No source could be located or verified, OR source exists behind paywall and content cannot be confirmed | Claim originates from model training knowledge without retrievable corroboration |

**UNVERIFIED is not a failure. It is honest uncertainty.** An LLM cannot verify the content of a paywalled paper. Assigning UNVERIFIED prevents false confidence. Consumers of the output decide whether to invest in manual verification.

For detailed grading criteria with examples: [evidence-grading.md](evidence-grading.md)

## Source Taxonomy

Sources are classified by type. Each type carries different quality signals:

| Type | Quality Signal | Typical Evidence Tier |
|------|---------------|----------------------|
| **Peer-reviewed paper** | Venue reputation, citation count, recency | STRONG (if corroborated) |
| **RFC / Specification** | Standards body authority (IETF, W3C, ISO) | STRONG |
| **Textbook** | Author credentials, edition count, publisher | MODERATE to STRONG |
| **Official documentation** | Maintained by the project/vendor, version-matched | MODERATE |
| **Whitepaper** | Author/org credibility, peer review status | MODERATE |
| **Conference talk / Video** | Venue reputation, speaker credentials | WEAK to MODERATE |
| **Blog post** | Author track record, technical depth, date | WEAK |
| **LLM training knowledge** | No retrievable source | UNVERIFIED |

For detailed source classification with quality heuristics: [source-taxonomy.md](source-taxonomy.md)

## Review Protocol

When conducting a literature review (whether via `/research` command or manually):

### Phase 1: Source Discovery
- Search for sources using WebSearch with domain-specific queries
- Catalog each source with metadata (title, author(s), year, type, URL/DOI)
- Aim for source diversity: at least 2 source types per domain
- Prefer primary literature (papers, RFCs, specs) over secondary (blogs, tutorials)

### Phase 2: Evidence Grading
- Read or fetch each source to extract key claims
- Assign evidence tier per claim using the grading scale above
- Cross-reference claims across sources to identify corroboration
- Flag any source that cannot be verified (paywall, broken URL) as UNVERIFIED

### Phase 3: Synthesis
- Group findings into thematic clusters
- Identify consensus (claims with STRONG evidence across sources)
- Identify controversy (conflicting claims from credible sources)
- Extract practical implications for the target domain

### Phase 4: Output Assembly
- Structure findings using the review-entry schema per source
- Produce thematic synthesis using the synthesis schema
- Write output to `.know/literature-{domain}.md` with proper frontmatter

## Schemas

- [review-entry.md](schemas/review-entry.md) -- Schema for a single literature review entry
- [synthesis.md](schemas/synthesis.md) -- Schema for cross-source thematic synthesis

## Hallucination Mitigation

LLMs fabricate citations. This protocol mitigates (does not eliminate) that risk:

1. **Never fabricate DOIs.** If you cannot retrieve a DOI via WebSearch, omit it. A missing DOI is better than a fake one.
2. **Use UNVERIFIED tier honestly.** When a claim comes from model training knowledge without a retrievable source, say so.
3. **Verify titles via WebSearch.** Before citing a paper, search for its exact title. If the search returns no results, downgrade to UNVERIFIED.
4. **Prefer linkable sources.** A source with a working URL that can be fetched carries more weight than one cited from memory.
5. **State the limitation.** Every literature output must include a methodology note acknowledging that findings are LLM-synthesized and citations should be independently verified.

## Output Integration

Literature review output follows `.know/` conventions:

```yaml
---
domain: "literature-{domain}"
generated_at: "{ISO 8601 UTC}"
expires_after: "180d"
source_scope: ["external-literature"]
generator: bibliotheca
confidence: {0.0-1.0}
format_version: "1.0"
---
```

Key differences from codebase `.know/` files:
- `expires_after` is `180d` (literature ages much slower than code; fast-moving domains can override with shorter expiry)
- `source_scope` is `["external-literature"]` (not file globs)
- `source_hash` is omitted (no codebase commit to track; empty `source_hash` is handled gracefully by `know.go:150-154`)
- `generator` is `bibliotheca` (not `theoros`)

## Consumers

- `/research` dromenon: Primary consumer. Loads this skill to structure its multi-pass execution.
- Any agent performing research: Can load this skill to structure ad-hoc literature citations in their work.
- `prompt-architect` (forge rite): Can consume `.know/literature-*.md` output as domain knowledge input.
