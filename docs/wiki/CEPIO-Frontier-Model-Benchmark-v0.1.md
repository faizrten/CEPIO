# CEPIO Frontier Model Benchmark v0.1

## Purpose

The frontier-model lane extends CEPIO Agent Challenge v0.1 from a single model/provider integration into a model-independent industrial reasoning benchmark.

The product question remains unchanged:

> Can a general-purpose frontier model understand and reason over an industrial enterprise through CEPIO without learning the underlying source-system implementation?

The frontier lane changes only the model/provider adapter. The CEPIO runtime, dataset, ten public challenge questions, tool schemas, final-answer contract, scorer and thresholds remain frozen.

## Benchmark invariants

A provider comparison is valid only when all of the following remain unchanged:

- Agent Challenge v0.1 question set;
- CEPIO runtime fixture and telemetry/waveform sizing;
- eight CEPIO semantic tools exposed to the model;
- system prompt and final-answer schema;
- hidden/public evaluator used by the engineering benchmark;
- scoring implementation and thresholds;
- direct source-system, repository, filesystem, shell and database access remain unavailable to the answering model.

Do not tune prompts, questions, scoring or tool schemas after seeing a model result and then present the tuned run as the first untuned result.

## Provider architecture

```text
Frozen Agent Challenge v0.1
          |
          +----------------------+----------------------+
          |                                             |
 GitHub Copilot SDK                         OpenAI Responses API
   model adapter                               model adapter
          |                                             |
      GPT-5.x                                Azure Foundry models
                                                        |
                                              gpt-6-astra / others
          +----------------------+----------------------+
                                 |
                         same CEPIO tool gateway
                                 |
                          same CEPIO runtime
```

`scripts/responses_api_agent.py` implements the OpenAI-compatible Responses API lane. It is intentionally configured through standard endpoint/model environment variables so another compatible provider can be tested without changing the benchmark harness.

## Responses API execution model

The frontier adapter:

1. receives only the natural-language question, CEPIO tool schemas and final-answer schema from the external-agent protocol;
2. sends the frozen system prompt and question to the configured Responses API model;
3. translates model function calls into CEPIO JSONL `tool_call` messages;
4. routes concurrent CEPIO tool results by request ID;
5. returns each CEPIO `tool_call_id` to the model so evidence citations remain scoreable;
6. carries all Responses output items forward locally and uses `store=false` rather than relying on server-side response history;
7. emits the same final JSON contract consumed by the existing Agent Challenge scorer.

The adapter does not expose raw CSV/JSON files, SQL, Python runtime objects, repository files, shell access or source-system connectors to the model.

## Azure Foundry setup

For the first frontier run, deploy `gpt-6-astra` (or use an Azure deployment name that points to that model) in an Azure OpenAI / Microsoft Foundry resource that supports the Responses API.

Add these GitHub Actions repository secrets:

- `AZURE_OPENAI_BASE_URL` — Azure OpenAI v1 base URL, for example `https://<resource>.openai.azure.com/openai/v1/`;
- `AZURE_OPENAI_API_KEY` — API key for that resource.

The workflow is manual-only:

`CEPIO Frontier Model Agent Challenge`

Its `model` input is the Azure deployment name. The default is `gpt-6-astra`.

For production or private qualification, prefer Microsoft Entra ID / workload identity over a long-lived API key. The API-key path exists here to keep the first controlled engineering experiment minimal and reproducible.

## Initial comparison matrix

Run the frozen benchmark independently for each model. Do not compare a tuned run from one provider with an untuned run from another.

| Lane | Suggested first model | Purpose |
| --- | --- | --- |
| GitHub Copilot SDK | `gpt-5.4` historical baseline | Existing live-agent baseline |
| Azure Foundry Responses | `gpt-6-astra` | Frontier intelligence ceiling |
| Azure Foundry Responses | `gpt-6.1-sol` | Strong production reasoning comparison |

Record at minimum:

- answer correctness;
- evidence coverage;
- unsupported claim count;
- identity accuracy;
- median CEPIO tool calls;
- median latency;
- semantic abstraction leakage;
- failed question IDs;
- provider, model/deployment and transport.

## Interpretation

A high score demonstrates that the tested model can operate through the CEPIO semantic abstraction on this synthetic benchmark. It does **not** by itself prove private industrial generalization.

The public repository currently contains inspectable benchmark fixtures/evaluator material, so this lane is an engineering benchmark. Qualification-grade claims require a versioned evaluator and holdout evidence that are unavailable to the answering process and not inspectable in the public repository.

The stronger future experiment is a controlled ablation:

1. frontier model + CEPIO semantic tools;
2. same frontier model + equivalent fragmented source representations without CEPIO;
3. compare accuracy, evidence quality, tool/interaction complexity and source-system leakage.

That experiment directly tests whether CEPIO increases the effective industrial intelligence and operational reliability of a frontier model rather than merely demonstrating that the model can answer the fixture questions.
