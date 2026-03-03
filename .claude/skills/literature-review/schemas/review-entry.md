# Schema: Literature Review Entry

## Template

```
### [SRC-NNN] {Title}
- **Authors**: {author list, or "Unknown" if not determinable}
- **Year**: {publication year, or "Unknown"}
- **Type**: {peer-reviewed paper | RFC/specification | textbook | official documentation | whitepaper | conference talk | blog post | LLM training knowledge}
- **URL/DOI**: {URL or DOI if available, or "Not available"}
- **Verified**: {yes: content fetched and confirmed | partial: title/abstract confirmed but full text not accessed | no: cited from model training knowledge}
- **Relevance**: {1-5 scale. 5 = directly addresses the domain question. 1 = tangentially related.}
- **Summary**: {2-4 sentences. What this source contributes to the domain question. Specific claims, not vague "discusses X."}
- **Key Claims**:
  - {Claim 1} [**{STRONG|MODERATE|WEAK|UNVERIFIED}**]
  - {Claim 2} [**{STRONG|MODERATE|WEAK|UNVERIFIED}**]
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number (001, 002, ...). Do not skip or reuse. |
| Title | Yes | Exact title of the source. Do not paraphrase. If uncertain, prefix with "Approximate title: ". |
| Authors | Yes | As attributed. "Unknown" is acceptable. Do not fabricate author names. |
| Year | Yes | Publication year. "Unknown" if not determinable. |
| Type | Yes | One of the defined source types from the source taxonomy. |
| URL/DOI | Conditional | Required if the source is online. "Not available" for books or inaccessible sources. Never fabricate DOIs. |
| Verified | Yes | Whether the source content was actually accessed and confirmed. Honest self-assessment. |
| Relevance | Yes | Integer 1-5. Justification is in the Summary. |
| Summary | Yes | What this source contributes. Must include specific claims, not just topic mention. |
| Key Claims | Yes | At least 1 claim per source. Each claim gets an independent evidence tier. |

## Example

```
### [SRC-001] Brewer's CAP Theorem -- Towards Robust Distributed Systems
- **Authors**: Eric Brewer
- **Year**: 2000
- **Type**: conference talk (ACM PODC Keynote)
- **URL/DOI**: Not available (keynote, not a published paper; formal proof in Gilbert & Lynch 2002)
- **Verified**: partial (keynote is widely cited; content known from secondary sources)
- **Relevance**: 5
- **Summary**: Introduced the conjecture that a distributed system can satisfy at most 2 of 3 properties: Consistency, Availability, and Partition tolerance. This framing became the foundational model for distributed systems design trade-offs. The conjecture was later formally proven by Gilbert and Lynch (2002).
- **Key Claims**:
  - Distributed systems face a fundamental trade-off among consistency, availability, and partition tolerance [**STRONG**]
  - The trade-off is a choice of 2-of-3, not a spectrum [**MODERATE** -- later work (e.g., Abadi 2012) argues PACELC provides a more nuanced model]
```

## Notes

- Entries are ordered by relevance (highest first), not by publication date.
- When multiple sources cover the same claim, cross-reference by SRC-NNN in the Key Claims.
- A single source may contribute claims at different evidence tiers (e.g., its core thesis is STRONG but a tangential claim is WEAK).
