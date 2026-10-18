# ADR-0013: Provider-neutral frontier-model Agent Challenge lane

- **Status:** Accepted
- **Date:** 2026-10-18
- **Decision owners:** CEPIO maintainers

## Context

CEPIO Agent Challenge v0.1 already has a live GitHub Copilot SDK lane and a preserved first untuned GPT-5.4 engineering result. The next experiment needs to determine whether the same CEPIO semantic abstraction can be operated by a different frontier model/provider without changing the benchmark contract.

Adding a GitHub Actions workflow is a protected governance change. The workflow can send benchmark questions and CEPIO tool results to an external model endpoint and can consume paid model capacity, so it must be opt-in, secret-scoped, and unable to weaken the existing CEPIO quality, governance, compatibility, security, or qualification gates.

## Decision

Add a provider-neutral OpenAI Responses API adapter and a manual-only Azure Foundry / Azure OpenAI benchmark workflow.

The following invariants are mandatory:

1. The Agent Challenge v0.1 questions, system prompt, CEPIO tool surface, final-answer schema, scorer, thresholds, telemetry sizing, and waveform sizing remain unchanged for the first untuned provider comparison.
2. The model process receives only the existing CEPIO semantic tool schemas and explicit tool results; it receives no direct repository, filesystem, shell, SQL, dataframe, or raw source-system access.
3. Concurrent model function calls are routed through the existing JSONL external-agent boundary with request/result correlation, and CEPIO `tool_call_id` values remain visible to the model for evidence citation.
4. Responses execution uses `store=false`; the adapter carries required response output and tool context locally between turns.
5. The live frontier workflow uses `workflow_dispatch` only. It does not run on push or pull request events and therefore cannot create unintentional model spend.
6. Credentials are supplied only through GitHub Actions secrets. No endpoint keys or tokens are committed to the repository or written to benchmark artifacts.
7. Provider/model metadata is attached only after the existing scorer has produced the report so provider wiring cannot alter scoring semantics.
8. Existing CEPIO CI, Quality Gate, Governance, Governance Protection, CodeQL, API compatibility, ontology compatibility, packaging, and container smoke gates remain enforced without exception.

## Initial implementation

The first supported frontier lane targets an Azure OpenAI / Microsoft Foundry Responses API endpoint with a deployment such as `gpt-6-astra`. The same adapter may later target another OpenAI-compatible endpoint by configuration, provided the benchmark invariants above remain unchanged.

The live workflow requires:

- `AZURE_OPENAI_BASE_URL`, pointing to the Azure OpenAI v1 base URL;
- `AZURE_OPENAI_API_KEY`, used only by the manually invoked benchmark job.

For production or private qualification, workload identity / Microsoft Entra authentication should replace a long-lived API key where supported by the execution environment.

## Validation

The change is accepted only when:

- normal CEPIO pytest and `make validate` pass;
- the new Responses adapter tests cover schema translation, concurrent function calls, request/result correlation, CEPIO evidence-ID preservation, stateless multi-turn execution, and client shutdown;
- CEPIO Quality Gate, including formatting, type ratchet, security, architecture, compatibility, and coverage-debt checks, passes;
- CodeQL passes;
- the manual frontier workflow is not invoked until an explicitly configured Azure model deployment and repository secrets exist.

The first live frontier-model result must be reported before any benchmark-informed prompt, question, tool-surface, or scoring changes are made.

## Consequences

### Positive

- CEPIO Agent Challenge becomes model/provider-neutral rather than a Copilot-specific demonstration.
- The GPT-5.4 Copilot result remains a historical baseline while stronger models can be compared against the same semantic boundary.
- The architecture supports a later CEPIO-vs-fragmented-source ablation experiment with the same frontier model.
- Manual invocation isolates model spend from normal CI.

### Trade-offs and limitations

- The current public engineering benchmark is not qualification-grade because fixture/evaluator material remains inspectable in the public repository.
- API-key authentication is acceptable for the first controlled engineering run but is not the desired production identity model.
- Model availability, deployment names, quota, latency, and price are external provider conditions and are recorded separately from CEPIO semantic correctness.

## Rejected alternatives

### Replace the Copilot lane

Rejected. Keeping both lanes preserves the historical baseline and makes provider comparison possible.

### Give the frontier model direct source files or repository access

Rejected. That would invalidate the CEPIO product hypothesis by changing the information boundary.

### Run the frontier workflow automatically on every push

Rejected. It would create uncontrolled external-model spend and make normal CI dependent on provider availability/quota.

### Tune the benchmark before recording the first frontier result

Rejected. The first frontier run is only scientifically useful if the benchmark remains frozen and the untuned result is preserved.
