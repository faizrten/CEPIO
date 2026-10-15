from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from time import perf_counter
from typing import Any, Protocol

from .model import PolicyEffect

TelemetryValue = str | int | float | bool


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TelemetryEvent:
    category: str
    operation: str
    success: bool
    duration_ms: float
    occurred_at: datetime = field(default_factory=_utcnow)
    attributes: dict[str, TelemetryValue] = field(default_factory=dict)


class TelemetrySink(Protocol):
    def emit(self, event: TelemetryEvent) -> None: ...


class NullTelemetrySink:
    def emit(self, event: TelemetryEvent) -> None:
        return None


class InMemoryTelemetrySink:
    def __init__(self) -> None:
        self.events: list[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent) -> None:
        self.events.append(event)

    def by_category(self, category: str) -> list[TelemetryEvent]:
        return [event for event in self.events if event.category == category]


class OpenTelemetrySink:
    """Optional OpenTelemetry adapter.

    `opentelemetry-api` is imported lazily so CEPIO core has no mandatory
    OpenTelemetry dependency. Install the `otel` extra to use this sink.
    """

    def __init__(self, tracer_name: str = "cepio.runtime") -> None:
        try:
            from opentelemetry import trace
            from opentelemetry.trace import Status, StatusCode
        except ImportError as exc:  # pragma: no cover - optional integration
            raise RuntimeError("OpenTelemetrySink requires `pip install cepio[otel]`") from exc
        self._tracer = trace.get_tracer(tracer_name)
        self._status_cls = Status
        self._status_code = StatusCode

    def emit(self, event: TelemetryEvent) -> None:
        span = self._tracer.start_span(f"cepio.{event.category}.{event.operation}")
        try:
            span.set_attribute("cepio.category", event.category)
            span.set_attribute("cepio.operation", event.operation)
            span.set_attribute("cepio.success", event.success)
            span.set_attribute("cepio.duration_ms", event.duration_ms)
            for key, value in event.attributes.items():
                span.set_attribute(f"cepio.{key}", value)
            span.set_status(
                self._status_cls(
                    self._status_code.OK if event.success else self._status_code.ERROR
                )
            )
        finally:
            span.end()


@contextmanager
def telemetry_operation(
    sink: TelemetrySink,
    *,
    category: str,
    operation: str,
    attributes: dict[str, TelemetryValue] | None = None,
) -> Iterator[None]:
    """Measure an integration/runtime operation without recording payloads.

    This is the public adapter boundary for future SAP/PI/OSDU/P6 integrations.
    Callers must pass identifiers/status metadata only, never source records or
    protected CEPIO properties.
    """

    started = perf_counter()
    success = False
    try:
        yield
        success = True
    finally:
        sink.emit(
            TelemetryEvent(
                category=category,
                operation=operation,
                success=success,
                duration_ms=(perf_counter() - started) * 1000,
                attributes=dict(attributes or {}),
            )
        )


class _RepositoryTelemetryProxy:
    def __init__(self, repository: Any, kind: str, sink: TelemetrySink) -> None:
        self._repository = repository
        self._kind = kind
        self._sink = sink

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._repository, name)
        if not callable(target) or name.startswith("_"):
            return target

        @wraps(target)
        def observed(*args: Any, **kwargs: Any) -> Any:
            with telemetry_operation(
                self._sink,
                category="repository",
                operation=name,
                attributes={"repository_kind": self._kind},
            ):
                return target(*args, **kwargs)

        return observed


class _PolicyTelemetryProxy:
    def __init__(self, policy_engine: Any, sink: TelemetrySink) -> None:
        self._policy_engine = policy_engine
        self._sink = sink

    def evaluate_action(self, request: Any, target: Any, definition: Any) -> Any:
        started = perf_counter()
        success = False
        effect = "error"
        try:
            decision = self._policy_engine.evaluate_action(request, target, definition)
            success = True
            effect = decision.effect.value
            return decision
        finally:
            duration_ms = (perf_counter() - started) * 1000
            attributes: dict[str, TelemetryValue] = {
                "action_type": request.action_type,
                "target_id": request.target.id,
                "actor_id": request.actor_id,
                "effect": effect,
            }
            self._sink.emit(
                TelemetryEvent(
                    category="policy",
                    operation="evaluate_action",
                    success=success,
                    duration_ms=duration_ms,
                    attributes=attributes,
                )
            )
            if success and effect != PolicyEffect.allow.value:
                self._sink.emit(
                    TelemetryEvent(
                        category="action",
                        operation=request.action_type,
                        success=False,
                        duration_ms=duration_ms,
                        attributes={
                            "target_id": request.target.id,
                            "actor_id": request.actor_id,
                            "outcome": "rejected",
                            "policy_effect": effect,
                        },
                    )
                )

    def can_read_type(self, roles: set[str], object_type: str) -> bool:
        return self._policy_engine.can_read_type(roles, object_type)

    def can_read_object(self, roles: set[str], obj: Any) -> bool:
        return self._policy_engine.can_read_object(roles, obj)

    def filter_properties(self, roles: set[str], obj: Any) -> Any:
        return self._policy_engine.filter_properties(roles, obj)

    def can_call_function(self, roles: set[str], function_name: str) -> bool:
        return self._policy_engine.can_call_function(roles, function_name)


def _wrap_action_handler(name: str, handler: Any, sink: TelemetrySink) -> Any:
    @wraps(handler)
    def observed(request: Any, target: Any, runtime: Any) -> Any:
        started = perf_counter()
        success = False
        try:
            result = handler(request, target, runtime)
            success = True
            return result
        finally:
            sink.emit(
                TelemetryEvent(
                    category="action",
                    operation=name,
                    success=success,
                    duration_ms=(perf_counter() - started) * 1000,
                    attributes={
                        "target_id": request.target.id,
                        "actor_id": request.actor_id,
                        "outcome": "executed" if success else "failed",
                    },
                )
            )

    return observed


def _wrap_function_handler(name: str, handler: Any, sink: TelemetrySink) -> Any:
    @wraps(handler)
    def observed(*args: Any, **kwargs: Any) -> Any:
        with telemetry_operation(sink, category="function", operation=name):
            return handler(*args, **kwargs)

    return observed


def instrument_runtime(runtime: Any, sink: TelemetrySink) -> Any:
    """Attach sanitized telemetry to a fully composed CEPIO runtime instance.

    The wrapper records operation names, duration, success/failure, stable object/action
    identifiers, and policy outcomes. It deliberately never serializes object properties,
    action parameters, handler effects, policy reasons, or returned payloads.
    """

    runtime.object_repository = _RepositoryTelemetryProxy(runtime.object_repository, "object", sink)
    runtime.event_repository = _RepositoryTelemetryProxy(runtime.event_repository, "event", sink)
    runtime.audit_repository = _RepositoryTelemetryProxy(runtime.audit_repository, "audit", sink)
    runtime.decision_repository = _RepositoryTelemetryProxy(runtime.decision_repository, "decision", sink)
    runtime.policy_engine = _PolicyTelemetryProxy(runtime.policy_engine, sink)

    for name, definition in runtime._actions.items():
        definition.handler = _wrap_action_handler(name, definition.handler, sink)
    for name, definition in runtime._functions.items():
        definition.handler = _wrap_function_handler(name, definition.handler, sink)

    original_register_action = runtime.register_action
    original_register_function = runtime.register_function

    def register_action(name: str, handler: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_register_action(name, handler, *args, **kwargs)
        runtime._actions[name].handler = _wrap_action_handler(name, runtime._actions[name].handler, sink)
        return result

    def register_function(name: str, handler: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_register_function(name, handler, *args, **kwargs)
        runtime._functions[name].handler = _wrap_function_handler(name, runtime._functions[name].handler, sink)
        return result

    runtime.register_action = register_action
    runtime.register_function = register_function
    runtime.telemetry_sink = sink
    return runtime
