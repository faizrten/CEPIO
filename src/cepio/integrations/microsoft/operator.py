"""Microsoft Harness orchestration for the existing governed Operator contract."""

from __future__ import annotations

import asyncio
from importlib.metadata import version


def run_operator(operator, *, question_id: str, question: str):
    """Run a fresh session; the existing gateway retains all execution authority.

    The planner proposes steps, the SDK owns function invocation, and CEPIO owns
    evidence and finalization. No model/provider or implicit tools are installed.
    """
    try:
        if version("agent-framework-core") != "1.24.0":
            raise ImportError("Unqualified agent framework version")
        import agent_framework as sdk
    except ImportError:
        raise RuntimeError(
            "Install cepio[agent-harness] for the Microsoft Operator runtime"
        ) from None

    from ...operator_agent import (
        FinalResponse,
        OperatorTraceEntry,
        ToolEvidence,
        ToolRequest,
        _stable_evidence_id,
    )

    tools = operator.gateway.list_tools()
    allowed = {str(item.get("name")) for item in tools if item.get("name")}
    trace = []
    evidence = []
    pending = None
    final = FinalResponse(status="INSUFFICIENT_CEPIO_EVIDENCE")
    turns = 0

    def dispatch(**arguments):
        nonlocal pending
        request = ToolRequest.model_validate(arguments)
        if pending is None or request != pending or len(trace) >= operator.max_tool_steps:
            raise ValueError("No matching bounded Operator request")
        pending = None  # Consume before the gateway, including failures.
        number = len(trace) + 1
        if request.name not in allowed:
            trace.append(
                OperatorTraceEntry(
                    step=number,
                    request=request,
                    error=f"Tool is not exposed by CEPIO gateway: {request.name}",
                )
            )
        else:
            try:
                payload = operator.gateway.call_tool(request.name, request.arguments)
                item = ToolEvidence(
                    id=_stable_evidence_id(request.name, request.arguments, payload),
                    tool_name=request.name,
                    arguments=request.arguments,
                    payload=payload,
                )
                evidence.append(item)
                trace.append(OperatorTraceEntry(step=number, request=request, evidence=item))
            except Exception as exc:
                trace.append(
                    OperatorTraceEntry(
                        step=number,
                        request=request,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        # Actual evidence stays in the typed CEPIO trace supplied to the planner.
        return "CEPIO gateway attempt recorded"

    class PlannerClient(sdk.FunctionInvocationLayer, sdk.BaseChatClient):
        async def _inner_get_response(self, *, messages, stream, options, **kwargs):
            nonlocal pending, final, turns
            if stream or pending is not None or turns >= operator.max_tool_steps + 1:
                raise ValueError("Operator model-turn bound exceeded")
            turns += 1
            step = operator.planner.next_step(
                question_id=question_id,
                question=question,
                tools=tools,
                trace=list(trace),
            )
            if isinstance(step, FinalResponse):
                final = step
            elif len(trace) < operator.max_tool_steps:
                if not isinstance(step, ToolRequest):
                    raise ValueError("Invalid Operator plan step")
                pending = step
                return sdk.ChatResponse(
                    messages=sdk.Message(
                        "assistant",
                        [
                            sdk.Content.from_function_call(
                                f"operator-{turns}",
                                "cepio_governed_dispatch",
                                arguments=step.model_dump(mode="json"),
                            )
                        ],
                    )
                )
            return sdk.ChatResponse(messages=sdk.Message("assistant", ["Operator complete"]))

    async def invoke():
        client = PlannerClient()
        client.function_invocation_configuration.update(
            {
                "max_iterations": operator.max_tool_steps + 1,
                "max_function_calls": operator.max_tool_steps,
                "allow_concurrent_invocation": False,
            }
        )
        agent = sdk.create_harness_agent(
            client,
            name="cepio-operator",
            tools=[
                sdk.tool(
                    dispatch,
                    name="cepio_governed_dispatch",
                    schema=ToolRequest,
                    description="Submit the pending request to the existing CEPIO policy gateway.",
                    # This internal dispatch is not an industrial approval. The gateway
                    # enforces the existing policy and independent human approvals.
                    approval_mode="never_require",
                )
            ],
            harness_instructions="Use only the governed CEPIO gateway.",
            disable_compaction=True,
            disable_todo=True,
            disable_mode=True,
            disable_file_memory=True,
            disable_web_search=True,
            auto_approval_rules=[],
        )
        await agent.run(question, session=agent.create_session())

    asyncio.run(invoke())
    return operator._finalize(question_id, final, trace, evidence)
