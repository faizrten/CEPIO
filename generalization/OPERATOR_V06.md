# CEPIO Operator v0.6

Operator v0.6 is the first executable agent boundary in the Generalization Lab.

## Boundary

The Operator may reason, plan and summarize, but enterprise facts may enter the agent loop only through a governed CEPIO tool gateway:

- CEPIO MCP facade; or
- CEPIO REST API.

`ConstrainedOperatorAgent` has no `CEPIORuntime` dependency. A planner therefore cannot reach repositories, fixture state or hidden enterprise data through the Operator API.

## Evidence discipline

Every successful tool result is wrapped as immutable tool evidence with a deterministic evidence ID derived from the tool name, arguments and returned CEPIO payload.

An `ANSWERED` response must cite at least one evidence ID produced in the current run. If it cites an unknown ID, the result becomes `REJECTED_UNSUPPORTED_EVIDENCE`.

If CEPIO cannot provide sufficient evidence, the correct result is `INSUFFICIENT_CEPIO_EVIDENCE`.

## Planner independence

The planner interface is provider-neutral. It may be backed by an LLM, a deterministic test planner or another reasoning engine. CI intentionally uses deterministic planners so model variability cannot control release qualification.

The model/planner never determines whether enterprise evidence is valid; CEPIO tool results and deterministic validation do.

## User context

Actor identity and roles are carried by the REST/MCP surface and CEPIO policy. They may constrain visibility or action authority, but they do not create persona-specific enterprise truth.

## Non-goals

Operator v0.6 does not add:

- a tenant control plane;
- a user-preference service;
- model memory as enterprise truth;
- direct repository access;
- web search as an enterprise-fact source.
