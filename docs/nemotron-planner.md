# Nemotron read-only planner binding

Status: opt-in implementation; live model quality, deployment and economics are
unqualified. No change to product release or scorecard. No new agent framework.

`cepio.nemotron_planner.NemotronPlanner` implements the existing `OperatorPlanner`
protocol and plugs into `ConstrainedOperatorAgent`. It uses a configured
OpenAI-compatible `/chat/completions` endpoint (base URL includes `/v1`). The
model must return the JSON step schema included in the prompt. This deliberately
does not assume vendor-specific JSON-schema or native tool-call support.

```python
from cepio.nemotron_planner import NemotronPlanner, NemotronSettings
from cepio.operator_agent import ConstrainedOperatorAgent

# gateway must already enforce authenticated actor/tenant authorization.
# Host must first admit source use, endpoint, credentials and spend.
planner = NemotronPlanner(NemotronSettings(
    base_url="https://approved-model-host.example/v1",
    model="operator-selected-pinned-nemotron-model",
    enabled=False,  # Explicit host enablement only after admission.
))
agent = ConstrainedOperatorAgent(gateway=authorized_gateway, planner=planner)
```

## Enforced boundaries

- Disabled by default; never discovers credentials or chooses an endpoint.
- Only `cepio_get_object` and `cepio_neighbors` proposals are accepted. The
  existing gateway executes them under its own authorization. No function calls,
  write tools, action execution or identity parameters are accepted.
- Model input contains only the supplied question, filtered tools and supplied
  read trace. This is not a tenant filter: the host must supply authorized data.
- HTTPS required except loopback development. Redirects, environment proxies,
  retries and provider fallbacks are disabled.
- Input byte limit, response byte limit, output-token cap and HTTP timeout.
  These bounds are not a financial budget or a total wall-clock deadline.
- Malformed, truncated, refused and unsupported responses abstain. Errors do not
  expose provider messages. Unknown citation IDs and uncited answers abstain.
- Citation membership proves a reference exists, not entailment, source freshness
  or engineering correctness. Downstream industrial validation remains necessary.
- No persistent prompt/response logging or shared cache. No training behavior.

## Qualification before default enablement

1. Pin model revision, runtime/image digest, precision, template and applicable
   licenses in the deployment record. A model alias alone is not a weight pin.
2. Verify private routing, authorized source use, secrets, GPU availability,
   timeout behavior and host-enforced spend/concurrency limits.
3. Run a synthetic live smoke test for JSON behavior and read-tool proposals.
4. In protected Labs, compare baseline model alone / baseline plus CEPIO /
   Nemotron alone / Nemotron plus CEPIO / deterministic CEPIO on held-out cases.
   Keep evidence access, scoring and budgets comparable; report critical errors,
   supported conclusions, abstention, latency and cost per successful case.
5. Retain an alternative backend and rollback by disabling this planner.

No endpoint, GPU, paid inference, customer deployment or default-provider switch
is provisioned by this change. No protected case data or answer keys are included.

## Validation

`pytest -q tests/test_nemotron_planner.py tests/test_operator_agent_v06.py`

Mock transport checks validate integration and failure handling, not Nemotron
intelligence. The end-to-end test uses the real Operator with a synthetic gateway.

References: [NVIDIA model catalogue](https://developer.nvidia.com/topics/ai/Nemotron),
[NIM offerings](https://docs.nvidia.com/nim/large-language-models/2.0.13/about-nim-llm/nim-offerings.html).

## Metered API pilot protocol (prepared 2026-11-07; not executed)

Use the merged adapter from PR #348. Prefer a metered hosted route for the first
evaluation; no dedicated GPU or fine-tuning is needed for this protocol.

### Bounded first run

- Proposed total ceiling: USD 10, including smoke tests, all model arms, failed
  calls and any paid judging. This is a planning ceiling, not an activated billing
  policy or permission to reuse another experiment's funds.
- First perform one synthetic compatibility call. Then run 12 frozen development
  cases across baseline alone, baseline with CEPIO, Nemotron alone, Nemotron with
  CEPIO, and deterministic CEPIO. Keep the cases and answer keys in protected Labs.
  Twelve cases are exploratory evidence, not qualification or proof of equivalence.
- Use identical case revisions, evidence-access entitlement and scoring rubric.
  Record actual evidence retrieved and tokens consumed; CEPIO treatment can change
  retrieval but must not receive privileged answer information. Score blind to arm.
- Fix per-case step limits, output-token limits and timeouts before execution.
  Sequential execution, no automatic retries or provider fallback.
- Estimate the maximum reservation for the complete run using the chosen routes
  and token limits before starting. If it exceeds the ceiling, reduce the planned
  sample or stop; do not silently expand the budget or partially compare arms.

### Admission and accounting

Live execution requires an explicitly selected HTTPS endpoint, model/deployment
identity, credential supplied through the host's secret mechanism, verified rates,
and an isolated enforceable budget. Never paste API keys into chat, documentation
or committed files. Reuse the governed host rather than introducing a second
budget service in Core. Existing zero-call policies remain effective until properly
configured; an application token limit or provider spending alert is not a hard cap.

The host must reserve the worst-case charge atomically before each outbound call,
including in-flight requests, all billable reasoning/output and provider fees.
Unknown tariffs or missing reservation evidence block dispatch. On an ambiguous
timeout retain the reservation until reconciled; do not assume a failed call is
free. Missing usage makes the cost unknown, not zero, and stops further calls
pending reconciliation. A soft provider balance/alert alone is insufficient.

The current planner returns an OperatorPlanStep and does not expose provider
usage receipts. The host transport/broker must capture metering before live
evaluation; this document does not implement that instrumentation or enforcement.

For every request retain a protected, prompt-free receipt:
run/case/arm ID, request ID, code SHA, model and provider revision, rate-card
timestamp, input/cache/output token counts under that provider's billing rules,
reasoning-token inclusion rule, reserved and reconciled USD, latency, completion
status and scoring outcome. Count reasoning once when already included in output.
Keep secrets and industrial evidence out of receipts published to Core.

### Decision report

Report paired case outcomes, critical errors, supported conclusions, correct
abstentions, unresolved cases, total calls, total cost, latency, and cost per
correctly resolved case. Include failures and retries in the numerator; zero
correct resolutions yields an undefined ratio, not zero cost. Report model charges
separately from retrieval, tools, infrastructure and engineering effort.

Do not adopt Nemotron by default on lower token prices alone. Advance to a larger
held-out evaluation only if the pilot shows no observed critical-error regression
and a promising cost/quality trade-off. This small sample cannot establish safety
or statistical non-inferiority. Preserve the baseline route for rollback.

### Activation handoff

Required configuration: approved endpoint base URL, exact model/deployment identity,
host secret reference (not its value), rate card, isolated budget scope and verified
remaining allowance. Public price examples are not the selected route's tariff.
Until these and host receipts are available, status is PREPARED / LIVE BLOCKED,
with no measured cost saving or judgment uplift.
