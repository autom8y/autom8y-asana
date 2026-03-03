# Evidence Grading Framework

## Tier Definitions

### STRONG

**Definition**: Claim is supported by 2 or more independent sources from primary literature (peer-reviewed papers, RFCs, official specifications, authoritative textbooks).

**Assignment criteria**:
- At least 2 sources assert the same claim independently
- Sources are from primary literature (not one blog quoting another)
- Sources are not from the same author/group (independent corroboration)
- Content of sources has been at least partially verified (abstract readable, DOI resolves, or full text fetched)

**Example**:
> "The CAP theorem proves that a distributed system cannot simultaneously provide Consistency, Availability, and Partition tolerance."
>
> - **Source 1**: Brewer, E. (2000). "Towards Robust Distributed Systems." ACM PODC Keynote. [Verified: widely cited, abstract available]
> - **Source 2**: Gilbert, S. & Lynch, N. (2002). "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services." ACM SIGACT News. [Verified: formal proof, full text available]
> - **Evidence tier**: STRONG (2 independent primary sources, formal proof exists)

### MODERATE

**Definition**: Claim is supported by 1 primary source, or by 2+ credible secondary sources (textbooks, official documentation, established conference presentations).

**Assignment criteria**:
- Single primary source with no independent corroboration, OR
- Multiple secondary sources that agree, OR
- Official documentation from the relevant project/vendor
- Source content partially verifiable

**Example**:
> "Go's garbage collector uses a concurrent, tri-color mark-and-sweep algorithm."
>
> - **Source**: Go team. "A Guide to the Go Garbage Collector." go.dev/doc/gc-guide. [Verified: official documentation, current]
> - **Evidence tier**: MODERATE (single official source, no independent analysis corroborating implementation details)

### WEAK

**Definition**: Claim is supported only by secondary sources (blog posts, tutorials, informal talks) or by a single non-peer-reviewed source.

**Assignment criteria**:
- Only blog posts or tutorials support the claim, OR
- Single non-peer-reviewed source, OR
- Source is dated (5+ years old in a fast-moving field) without recent corroboration
- Claim is plausible but lacks authoritative backing

**Example**:
> "Most production Go services see a 10-15% throughput improvement when switching from sync.Mutex to sync.RWMutex for read-heavy workloads."
>
> - **Source**: Blog post by a Go developer describing their benchmarks (2023). [Verified: URL resolves, benchmarks shown]
> - **Evidence tier**: WEAK (single blog post, benchmark methodology not peer-reviewed, results may not generalize)

### UNVERIFIED

**Definition**: No retrievable source supports the claim, or the source exists but its content cannot be confirmed (e.g., behind paywall).

**Assignment criteria**:
- Claim originates from model training knowledge with no retrievable source, OR
- Source exists but is paywalled and content cannot be confirmed, OR
- WebSearch for the exact claim or paper title returns no results, OR
- Source URL is broken or domain is defunct

**UNVERIFIED is honest, not shameful.** It means: "I believe this is true based on my training data, but I cannot point you to a source you can check yourself."

**Example**:
> "Ousterhout's RAMCloud project demonstrated that end-to-end latency below 5 microseconds is achievable for key-value operations over RDMA."
>
> - **Source**: Recalled from training data. Paper title and approximate year known, but DOI not retrievable and full text not fetched.
> - **Evidence tier**: UNVERIFIED (claim is plausible and consistent with known RAMCloud publications, but specific latency figure not independently confirmed)

## Tier Upgrade / Downgrade Rules

| Action | When |
|--------|------|
| Upgrade WEAK to MODERATE | A second credible source is found that independently asserts the same claim |
| Upgrade MODERATE to STRONG | A second independent primary source is found |
| Upgrade UNVERIFIED to any tier | A retrievable source is found and at least partially verified |
| Downgrade STRONG to MODERATE | One of the two sources is retracted, found to be from the same author group, or content contradicts on closer reading |
| Downgrade any tier to UNVERIFIED | Source URL breaks, paper is retracted, or content behind paywall cannot be confirmed |

## Aggregation Rules

When a `.know/literature-{domain}.md` file contains multiple claims at different tiers:

- **Overall confidence** = weighted average: STRONG=1.0, MODERATE=0.7, WEAK=0.4, UNVERIFIED=0.2
- If more than 50% of claims are UNVERIFIED, the overall confidence MUST be below 0.5
- If any STRONG claim contradicts another STRONG claim, flag as controversy (do not average away the conflict)

## Domain Calibration Signal

When computing final evidence distribution, assess the distribution shape:

- **>80% STRONG claims**: Append to output: "High confidence distribution reflects a well-studied domain with canonical literature. For less-established domains, expect more MODERATE/UNVERIFIED claims. Evidence grades reflect training data density, not independent verification rigor."
- **>50% UNVERIFIED claims**: Append to output: "Low confidence distribution reflects a domain with sparse or paywalled primary literature. Treat findings as starting points for manual research, not as settled knowledge."
- **Mixed distribution**: No calibration note needed — the distribution itself communicates uncertainty honestly.
