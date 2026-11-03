# Copilot harness ↔ CEPIO Foundry G1 comparison (proposal)

**Classification:** PUBLIC integration and qualification plan  
**Status:** NOT RUN / NOT QUALIFIED — no Azure deployment, inference, credential grants or release claim  
**Owner work item:** [#321](https://github.com/faizrten/CEPIO/issues/321)  
**Existing gate:** [G1 #248](https://github.com/faizrten/CEPIO/issues/248), under [Reliability Lighthouse #246](https://github.com/faizrten/CEPIO/issues/246)  
**As-of:** 2026-11-03

## Decision and reuse

**Microsoft owns generic agent execution. CEPIO owns industrial agency.** The initial experiment tests whether the optional Microsoft Copilot harness improves CEPIO's K-101 investigation against the existing Foundry agent **without** changing CEPIO Core semantics, gateway, identity model, Skill admission or industrial authority.

Reuse:
- `scripts/run_foundry_reliability_g1.py` and `tests/test_foundry_reliability_g1.py`;
- `docs/foundry-reliability-g1.md` (all G1 acceptance gates);
- existing authenticated `/mcp` and exactly the six G1-allowed CEPIO tools;
- current protected Reliability Skill and synthetic evaluation assets from CEPIO Labs.

Do **not** build a generic agent scheduler, planner, shell-agent gateway, extra MCP service, persistent agent session schema or another industrial action path.

## Preconditions: G1 before comparison

A passing local test suite or the public runner's `PASS` is **not** a live G1 qualification. A real Foundry agent must invoke the qualified Reliability Skill through verified Entra identity and return a governed Decision. A trusted host-side query must independently verify Decision persistence, subject, current-run evidence and trace lineage. The host must **not** be able to reach direct Fabric/PI/SAP credentials or CEPIO repository internals. No action or recommendation tools are exposed.

**Stop without deploying the harness** if the required verified authenticated CEPIO MCP tool binding is unsupported by this preview, if the Skill is not READY, or if an exact role/tool boundary cannot be enforced. Do not replace it with a direct API or credential bypass.

## Two isolated host configurations

**Control — Standard Foundry G1:** retain the existing prompt-agent configuration and reference runner, with no unrelated changes.

**Candidate — Copilot harness:** create a separate preview prompt agent, never convert the control agent in place. The host selection is:

```yaml
# Illustrative fragment: merge into a new agent's azure.yaml.
services:
  cepio-reliability-copilot-preview:
    host: azure.ai.agent
    harness:
      type: microsoft_copilot_preview
    tools:
      - type: microsoft_copilot_toolset_preview
        defaultConfig:
          enabled: false
```

The fragment deliberately disables all five built-in harness tools at the start, including `shell`, `web`, `filesystem_read`, `filesystem_write`, and `subagents`. Attach **only** the approved existing CEPIO remote MCP capability through a Microsoft-documented, supported project connection/toolbox mechanism after verifying the persisted agent definition. Existing CEPIO actor/policy/approval gates are authoritative regardless of Foundry tool switches.

Do not enable subagents during G1. Test delegated planning only after the baseline evidence/Decision proof is qualified, as a separately versioned extension. Never treat a disabled filesystem/web toggle as a complete sandbox boundary when shell is enabled.

## Experimental design

| Arm | Managed host | Industrial capabilities | Purpose |
| --- | --- | --- | --- |
| A | Standard Foundry prompt agent | Same bounded CEPIO MCP Skills | Current G1 control |
| B | New Copilot harness prompt agent | Same bounded CEPIO MCP Skills | Marginal harness value |

Hold model and version, scenario version, K-101 evidence snapshot, task prompt, allowed CEPIO tools, permissions and completion rubric constant when the preview permits. If model parity is impossible, record a confounder and do not claim a controlled harness-only uplift. Keep protected evaluation corpus and grading rules exclusively in CEPIO Labs. No customer data.

**Suggested cases:** (1) complete synthetic evidence; (2) missing material evidence; (3) inconsistent dated records; (4) recoverable tool error; (5) forbidden action request; (6) wrong tenant/actor attempt; (7) invented source reference. Negative scenarios must fail closed without fabricated conclusions.

**Minimum per-run artifact:** agent kind/harness/version, model/version, scenario ID/hash, source snapshot and available-at time, prompt/hash, allowed tool list, verified Entra actor mapping (no tokens), correlation ID, actual MCP call/result trace, material evidence IDs, Decision ID, independent Decision verification record, forbidden-tool count, error/recovery sequence, wall time, model tokens, and measured service cost. Scrub sensitive metadata before public reporting.

## Qualification and adoption gate

All hard gates must pass before interpreting performance:
1. Foundry invocation and structured `cepio_evaluate_skill` call, Skill READY and non-error result;
2. independently persisted current-run Decision with traceable material evidence;
3. zero unapproved external Actions or direct source/API bypass;
4. independently verified identity, tenant, least-privilege role and policy;
5. no fabricated material claim, tenant leak or unauthorized tool invocation.

Then compare decision correctness, evidence coverage, decision time, tool-call/error recovery, cost and operational usefulness. A harness win requires a material, reproducible improvement in at least one outcome metric without weakening a hard gate. Do not count vendor-reported generic benchmark uplifts as CEPIO evidence. Keep G1 open until real live qualification and record the comparison as a **separate** evaluation, not automatic scorecard credit.

## Authorization / scope boundary

Budget default **USD 0 for this planning PR**. No paid inference, resource creation, Entra grants, production deployment or runtime changes are authorized by this document. Verify an enforceable spend ceiling before any later live run; quotas alone are not guaranteed currency caps. Foundry Copilot harness is a preview with no production SLA.

## Sources

- [Existing CEPIO G1 qualification](../foundry-reliability-g1.md)
- [Microsoft Foundry Copilot harness instructions](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/use-tools-skills-copilot-harness)
- [CEPIO Microsoft-native industrial-agency boundary](../adr/ADR-0032-microsoft-native-industrial-agency.md)
