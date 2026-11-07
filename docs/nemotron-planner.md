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
