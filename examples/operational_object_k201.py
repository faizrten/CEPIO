"""Offline synthetic K-201 Operational Object inspection.

Run from the repository root:
    PYTHONPATH=src python examples/operational_object_k201.py

Demonstrates local application composition only. No live PI/SAP, cloud calls, source
attestation, identity-token verification, decision persistence or Action execution.
"""

from __future__ import annotations

import json
from pathlib import Path

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.model import OntologyObject, Relationship
from cepio.operational_object_inspection import inspect_operational_object


def main() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "satorp_hydrocracker.json").read_text(encoding="utf-8")
    )
    runtime = build_runtime()
    for obj in fixture["objects"]:
        runtime.upsert_object(OntologyObject.model_validate(obj))
    for rel in fixture["relationships"]:
        runtime.add_relationship(Relationship.model_validate(rel))

    # Local fixture identity only: this is NOT an authenticated enterprise session.
    host_context = ExecutionContext(
        actor_id="offline-reference-host",
        actor_roles=frozenset({"cepio_admin"}),
        correlation_id="synthetic-k201-operational-object-v01",
    )
    view = inspect_operational_object(
        CEPIOApplicationService(runtime),
        "K-201",
        host_context,
    )
    print(view.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
