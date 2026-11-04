"""Linux process qualification only; no worker registration in production code."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux OS limits require Linux evidence; no unbounded fallback"
)

WORKER = Path(__file__).parent / "fixtures" / "relationship_process_worker.py"


class WorkerUnavailable(RuntimeError):
    pass


class Worker:
    """Test-only fixed child supervisor with bounded pipes and no restart."""

    def __init__(self, directory, tenant, mode="normal"):
        self.dead = False
        self.last_report = None
        self.failure_type = None
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                str(WORKER.resolve()),
                str(directory / f"{tenant}.db"),
                tenant,
                mode,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "LD_LIBRARY_PATH": str(Path(sys.executable).resolve().parent.parent / "lib"),
            },
            start_new_session=True,
        )
        try:
            self.ready = self._frame(15)
            if self.ready.get("ready") is not True:
                raise WorkerUnavailable("Relationship query unavailable")
        except Exception as exc:
            self.failure_type = type(exc).__name__
            self.close()
            raise WorkerUnavailable("Relationship query unavailable") from None

    def _frame(self, timeout):
        import select

        deadline = time.monotonic() + timeout
        result = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise TimeoutError
            chunk = os.read(self.process.stdout.fileno(), min(4096, 262_145 - len(result)))
            if not chunk:
                raise EOFError
            result.extend(chunk)
            if len(result) > 262_144:
                raise BufferError
            if b"\n" in result:
                if result.index(b"\n") != len(result) - 1:
                    raise WorkerUnavailable("Relationship query unavailable")
                return json.loads(result)

    def read(self, query, timeout=2):
        if self.dead:
            raise WorkerUnavailable("Relationship query unavailable")
        # Bound input before writing. With one synchronous outstanding request,
        # this frame fits Linux PIPE_BUF; no output is collected with communicate().
        raw = json.dumps(query).encode() + b"\n"
        if len(raw) > 4096:
            raise WorkerUnavailable("Relationship query unavailable")
        try:
            self.process.stdin.write(raw)
            self.process.stdin.flush()
            report = self._frame(timeout)
            self.last_report = report
            if report.get("outcome") != "page":
                raise WorkerUnavailable("Relationship query unavailable")
            return report["page"]
        except Exception as exc:
            self.failure_type = type(exc).__name__
            self.close()
            raise WorkerUnavailable("Relationship query unavailable") from None

    def close(self):
        self.dead = True
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.process.wait(timeout=3)
        self.process.stdin.close()
        self.process.stdout.close()


@pytest.fixture
def workers(tmp_path):
    launched = []

    def launch(tenant, mode="normal"):
        worker = Worker(tmp_path, tenant, mode)
        launched.append(worker)
        return worker

    yield launch
    for worker in launched:
        worker.close()


def test_limits_cover_runtime_construction_and_source_aware_pagination(
    workers, monkeypatch, record_property
):
    monkeypatch.setenv("CEPIO_TEST_CREDENTIAL_SENTINEL", "synthetic-not-a-credential")
    worker = workers("tenant-a")
    assert worker.ready["as_limit"] == [1_073_741_824] * 2
    assert worker.ready["cpu_limit"] == [5, 5]
    assert worker.ready["core_limit"] == [0, 0]
    assert worker.ready["nofile_limit"] == [64, 64]
    assert worker.ready["credential_inherited"] is False
    first = worker.read({"asset_id": "asset", "limit": 1})
    assert first["subject"]["properties"] == {"status": "tenant-a"}
    assert len(first["links"]) == 1 and first["next_cursor"]
    second = worker.read({"asset_id": "asset", "limit": 1, "cursor": first["next_cursor"]})
    assert len(second["links"]) == 1 and second["next_cursor"] is None
    record_property("linux_process_limits", json.dumps(worker.ready))
    record_property("linux_process_peak_rss_kib", worker.last_report["maxrss_kib"])
    print(json.dumps({"limits": worker.ready, "peak_rss_kib": worker.last_report["maxrss_kib"]}))


@pytest.mark.parametrize("mode", ["python_memory", "native_memory", "sqlite_memory"])
def test_memory_failure_is_contained_and_peer_remains_available(workers, mode, record_property):
    failing = workers("tenant-a", mode)
    healthy = workers("tenant-b")
    with pytest.raises(WorkerUnavailable, match="^Relationship query unavailable$"):
        failing.read({"asset_id": "asset"})
    assert failing.last_report["allocation_denied"] is True
    assert failing.ready["pid"] != healthy.ready["pid"]
    assert failing.dead and failing.process.poll() is not None
    assert healthy.read({"asset_id": "asset"})["subject"]["properties"] == {"status": "tenant-b"}
    pid = failing.process.pid
    with pytest.raises(WorkerUnavailable):
        failing.read({"asset_id": "asset"})
    assert failing.process.pid == pid  # no restart or hidden capacity reset
    record_property("contained_memory_fault", json.dumps({"mode": mode, **failing.last_report}))


def test_runaway_cpu_is_killed_by_os_while_peer_reads(workers):
    failing, healthy = workers("tenant-a", "cpu"), workers("tenant-b")
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(failing.read, {"asset_id": "asset"}, 10)
        assert healthy.read({"asset_id": "asset"})["links"]
        with pytest.raises(WorkerUnavailable):
            future.result(timeout=12)
    assert failing.process.returncode == -signal.SIGKILL
    assert failing.failure_type == "EOFError"
    assert healthy.read({"asset_id": "asset"})["links"]


def test_blocking_callback_is_killed_and_reaped_by_supervisor(workers):
    failing, healthy = workers("tenant-a", "hang"), workers("tenant-b")
    started = time.monotonic()
    with pytest.raises(WorkerUnavailable):
        failing.read({"asset_id": "asset"}, timeout=0.5)
    assert time.monotonic() - started < 5
    assert failing.failure_type == "TimeoutError"
    assert failing.process.returncode == -signal.SIGKILL
    assert healthy.read({"asset_id": "asset"})["links"]


@pytest.mark.parametrize("mode", ["crash", "oversized_output"])
def test_crash_or_oversized_ipc_fails_closed_without_restart(workers, mode):
    failing = workers("tenant-a", mode)
    with pytest.raises(WorkerUnavailable):
        failing.read({"asset_id": "asset"})
    assert failing.dead and failing.process.poll() is not None
    if mode == "crash":
        assert failing.process.returncode == 77


def test_stderr_is_not_an_unbounded_parent_buffer(workers):
    worker = workers("tenant-a", "stderr")
    assert worker.read({"asset_id": "asset"})["links"]
    assert worker.process.stderr is None


def test_oversized_request_rejected_before_dispatch_without_disabling_worker(workers):
    worker = workers("tenant-a")
    with pytest.raises(WorkerUnavailable):
        worker.read({"asset_id": "x" * 5000})
    assert worker.read({"asset_id": "asset"})["links"]


def test_worker_reuses_scope_and_current_rights_checks(workers):
    worker = workers("tenant-a", "revocation")
    first = worker.read({"asset_id": "asset", "limit": 1})
    with pytest.raises(WorkerUnavailable):
        worker.read({"asset_id": "asset", "limit": 1, "cursor": first["next_cursor"]})
    other = workers("tenant-b")
    with pytest.raises(WorkerUnavailable):
        other.read({"asset_id": "asset", "tenant_id": "tenant-a"})


def test_failed_limit_setup_never_admits_a_worker(tmp_path):
    with pytest.raises(WorkerUnavailable):
        Worker(tmp_path, "tenant-a", "limit_failure")
    assert not (tmp_path / "tenant-a.db").exists()
