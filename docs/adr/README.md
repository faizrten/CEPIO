# CEPIO Architecture Decision Records

Architecture Decision Records capture durable CEPIO design constraints without turning every architectural concern into a runtime subsystem.

Current foundational constraints include:

- `ADR-006-enterprise-knowledge-sovereignty.md` — enterprise truth remains enterprise-owned; canonical CEPIO semantics contain no customer IP; user context changes view/authority rather than truth; cross-enterprise learning promotes abstractions only.
- `ADR-007-open-interface-protected-intelligence.md` — CEPIO remains open at the interface and interoperability layer while differentiated implementation and industry intelligence may remain protected; publication is an explicit architectural decision.
- `ADR-008-core-evidence-uncertainty.md` — evidence, claims, assumptions, uncertainty, confidence, dependency and information gain are CEPIO Core semantics; domains provide uncertain characteristics and specialized engines provide quantitative computation.
- `ADR-009-opportunity-as-kinetic-primitive.md` — opportunity, option and authority-neutral `OptionRecommendation` are universal Kinetic semantics that bridge evidence/uncertainty to governed decisions without introducing an ambiguous second `Recommendation` type.
- `ADR-0010-drilling-domain-qualification-benchmark.md` — the Drilling Contractor qualification benchmark remains an additive generalization and validation capability, not canonical ontology content.
- `ADR-0011-agent-challenge-evaluator-isolation.md` — public synthetic fixtures and challenge questions are separated from the private qualification evaluator; a public answer key cannot be represented as a hidden live-agent benchmark.
