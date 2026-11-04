"""Linux-only synthetic worker fixture. Not a production host or worker service.

Run as a fresh interpreter; enforce OS limits before importing/building CEPIO.
Only the local qualification tests launch this fixed fixture.
"""

import ctypes
from datetime import datetime, timedelta, timezone
import json
import os
import resource
import sqlite3
import sys
import time

AS_BYTES = 1_073_741_824
CPU_SECONDS = 5


def main():
    database, tenant, mode = sys.argv[1:]
    if mode == "limit_failure":
        raise OSError("Synthetic resource setup failure")
    # Hard limits too: this trusted fixture never raises them again. A privileged
    # or malicious process is outside this qualification's threat model.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

    from cepio.application_contract import CEPIOApplicationService, ExecutionContext
    from cepio.bootstrap import build_runtime
    from cepio.model import ObjectRef, OntologyObject, Relationship
    from cepio.policy import RolePolicyEngine
    from cepio.relationship_qualification import (
        RelationshipQualificationBoundary,
        RelationshipQualificationUnavailable,
    )
    from cepio.relationship_query import (
        RelationshipSourceAccess,
        RelationshipVisibility,
        SQLiteRelationshipPageAdapter,
    )

    runtime = build_runtime(sqlite_path=database, validate_types=False, validate_properties=False)
    runtime.policy_engine = RolePolicyEngine(
        {
            "reader": {
                "read_types": ["Asset", "Order"],
                "read_properties": {"Asset": ["status"], "Order": ["status"]},
            }
        }
    )
    repo = runtime.object_repository
    adapter = SQLiteRelationshipPageAdapter(repo)
    for identifier, kind in (("asset", "Asset"), ("order", "Order")):
        repo.upsert_object(
            OntologyObject(
                id=identifier, type=kind, properties={"status": tenant, "secret": "never returned"}
            )
        )
        adapter.bind_object(identifier, tenant_id=tenant)
        adapter.bind_object_sources(identifier, frozenset({"synthetic-source"}))
    for identifier in ("r1", "r2"):
        repo.add_relationship(
            Relationship(
                id=identifier,
                type="hasOrder",
                source=ObjectRef(id="asset", type="Asset"),
                target=ObjectRef(id="order", type="Order"),
            )
        )
        adapter.bind_relationship(
            identifier, tenant_id=tenant, classification="ordinary", source_use="inspect"
        )
        adapter.bind_relationship_sources(identifier, frozenset({"synthetic-source"}))
    context = ExecutionContext(
        actor_id="host-user", tenant_id=tenant, actor_roles=frozenset({"reader"})
    )
    access = RelationshipSourceAccess(
        actor_id=context.actor_id,
        tenant_id=tenant,
        actor_roles=context.actor_roles,
        source_ids=frozenset({"synthetic-source"}),
        rights_version="v1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    visibility = RelationshipVisibility(
        relationship_types=frozenset({"hasOrder"}),
        classifications=frozenset({"ordinary"}),
        source_uses=frozenset({"inspect"}),
        policy_version="v1",
    )
    diagnostics = {"allocation_denied": False}
    calls = 0

    def rights(_context):
        nonlocal calls
        calls += 1
        if mode == "python_memory":
            try:
                bytearray(AS_BYTES * 2)
            except MemoryError:
                diagnostics["allocation_denied"] = True
                raise
            raise AssertionError("Address-space limit did not reject allocation")
        if mode == "native_memory":
            libc = ctypes.CDLL(None)
            libc.malloc.argtypes = [ctypes.c_size_t]
            libc.malloc.restype = ctypes.c_void_p
            libc.free.argtypes = [ctypes.c_void_p]
            pointer = libc.malloc(AS_BYTES * 2)
            if pointer:
                libc.free(pointer)
                raise AssertionError("Native allocation bypassed address-space limit")
            diagnostics["allocation_denied"] = True
            raise MemoryError
        if mode == "sqlite_memory":
            with sqlite3.connect(":memory:") as fault:
                fault.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, AS_BYTES + 1024)
                try:
                    fault.execute("SELECT randomblob(?)", (AS_BYTES,)).fetchone()
                except MemoryError:
                    diagnostics["allocation_denied"] = True
                    raise
            raise AssertionError("SQLite allocation bypassed address-space limit")
        if mode == "cpu":
            while True:
                pass
        if mode == "hang":
            time.sleep(60)
        if mode == "crash":
            os._exit(77)
        if mode == "revocation" and calls > 1:
            return access.model_copy(update={"rights_version": "revoked-v2"})
        return access

    boundary = RelationshipQualificationBoundary(
        CEPIOApplicationService(runtime), adapter, lambda: context, lambda _: visibility, rights
    )
    print(
        json.dumps(
            {
                "ready": True,
                "pid": os.getpid(),
                "as_limit": resource.getrlimit(resource.RLIMIT_AS),
                "cpu_limit": resource.getrlimit(resource.RLIMIT_CPU),
                "core_limit": resource.getrlimit(resource.RLIMIT_CORE),
                "nofile_limit": resource.getrlimit(resource.RLIMIT_NOFILE),
                "credential_inherited": "CEPIO_TEST_CREDENTIAL_SENTINEL" in os.environ,
            }
        ),
        flush=True,
    )
    try:
        while True:
            raw = sys.stdin.buffer.readline(4097)
            if not raw:
                return
            if len(raw) > 4096 or not raw.endswith(b"\n"):
                return
            if mode == "oversized_output":
                os.write(sys.stdout.fileno(), b"x" * 262_145)
                return
            if mode == "stderr":
                os.write(sys.stderr.fileno(), b"x" * 1_000_000)
            try:
                page = boundary.read(json.loads(raw))
                report = {"outcome": "page", "page": page.model_dump(mode="json")}
            except RelationshipQualificationUnavailable:
                report = {"outcome": "unavailable"}
            report.update(diagnostics)
            report["maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            print(json.dumps(report), flush=True)
    finally:
        repo.close()


if __name__ == "__main__":
    main()
