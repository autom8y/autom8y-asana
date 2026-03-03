# Source Taxonomy

## Source Types

### Peer-Reviewed Paper

**Definition**: Published in a journal or conference with a formal peer review process.

**Quality signals**:
- Venue reputation (ACM, IEEE, USENIX, VLDB, SIGMOD, OSDI, SOSP, etc.)
- Citation count (relative to age -- 50 citations in 2 years is different from 50 in 20 years)
- Author institutional affiliation
- Recency (recent papers in active fields reflect current understanding)

**Verification approach**: Search for exact title via WebSearch. Check if DOI resolves. Read abstract if available. If full text is paywalled, note this and use MODERATE at best.

**Common trap**: LLMs fabricate plausible-sounding paper titles. Always verify title existence via WebSearch before citing.

### RFC / Specification

**Definition**: Standards document published by a recognized standards body (IETF, W3C, ISO, ECMA, IEEE Standards).

**Quality signals**:
- Standards body authority (IETF RFCs carry protocol authority; W3C specs carry web standard authority)
- RFC status: Standards Track > Informational > Experimental > Historic
- Version currency (superseded RFCs should reference the replacement)

**Verification approach**: RFCs are freely available at rfc-editor.org and tools.ietf.org. W3C specs at w3.org/TR/. Always fetch to confirm content.

**Common trap**: Citing an obsoleted RFC without noting its replacement. Always check "Obsoleted by" header.

### Textbook

**Definition**: Published book by a recognized academic or technical publisher, covering a field systematically.

**Quality signals**:
- Author credentials (university professor, industry leader, recognized expert)
- Edition count (multiple editions suggest sustained relevance)
- Publisher reputation (O'Reilly, Addison-Wesley, MIT Press, Springer, etc.)
- Adoption (used in university courses, cited in papers)

**Verification approach**: Search for ISBN or exact title. Check publisher catalog. Edition and year are verifiable; specific page claims are not (without the book).

**Common trap**: Misattributing a claim to a textbook chapter when the claim is actually the LLM's synthesis. Cite textbooks for established frameworks and definitions, not for specific data points.

### Official Documentation

**Definition**: Documentation maintained by the project, vendor, or organization that created the technology.

**Quality signals**:
- Maintained and versioned (docs matching the software version in question)
- Published on the project's official domain
- Written or reviewed by core contributors

**Verification approach**: Fetch the URL. Check that the content matches the claim. Note the documentation version.

**Common trap**: Citing documentation for a different version than the one being discussed. Always note the version.

### Whitepaper

**Definition**: Technical document published by a company or research group, typically not peer-reviewed but presenting original technical content.

**Quality signals**:
- Author/organization credibility (Google, Meta, Amazon research papers on their own systems)
- Technical depth (architecture details vs. marketing content)
- Whether it was later published as a peer-reviewed paper

**Verification approach**: Often available as PDFs on company blogs or research pages. Fetch if possible.

**Common trap**: Treating vendor whitepapers as peer-reviewed research. A Google whitepaper about Spanner is authoritative about Spanner's design, but its claims about competing systems may not be.

### Conference Talk / Video

**Definition**: Recorded presentation at a technical conference, meetup, or webinar.

**Quality signals**:
- Conference reputation (KubeCon, Strange Loop, GopherCon, GOTO, QCon vs. local meetup)
- Speaker credentials (core contributor, recognized expert, vs. unknown)
- Slides/transcript availability (easier to verify specific claims)

**Verification approach**: Search for talk title + speaker name. Check if slides or video are available. Specific claims from talks are harder to verify than written sources.

**Common trap**: Citing "a talk I saw" without title, speaker, or venue. If you cannot provide these, use UNVERIFIED.

### Blog Post

**Definition**: Article published on a personal or company blog, Medium, dev.to, or similar platform.

**Quality signals**:
- Author track record (recognized contributor vs. anonymous)
- Technical depth (benchmarks, code, architecture diagrams vs. opinion)
- Date (recent in fast-moving fields)
- Comments/discussion quality (peer feedback visible)

**Verification approach**: Fetch the URL. Assess technical rigor. Note that blog posts are not peer-reviewed.

**Common trap**: Treating popular blog posts as authoritative. Popularity does not equal correctness. A widely-shared blog post with flawed benchmarks is still WEAK evidence.

### LLM Training Knowledge

**Definition**: Information recalled from model training data without a retrievable, verifiable source.

**Quality signals**: None that can be externally verified. The claim may be accurate (training data included the source) but the consumer cannot check.

**Verification approach**: None. This is the UNVERIFIED tier by definition.

**Honest framing**: "Based on my training data, I recall that X. I was unable to locate a retrievable source to verify this claim."
