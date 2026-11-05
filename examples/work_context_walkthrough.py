"""Synthetic evidence-readiness walkthrough; no engineering diagnosis or live source."""

import json
from datetime import datetime, timedelta, timezone

from cepio.accc_host_admission import HostPrincipal
from cepio.work_context import (
    EvidenceReceipt,
    WorkContextRequest,
    WorkQuestion,
    WorkSnapshot,
    read_work_context,
)

AT = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


class SyntheticHost:
    def __init__(self):
        self.snapshot = WorkSnapshot(
            work_id="synthetic-quality-investigation",
            tenant_id="synthetic",
            revision=1,
            objective="Establish evidence needed to investigate recurring quality losses",
            questions=(
                WorkQuestion(
                    id="evidence-readiness",
                    stage="assess",
                    text="Which evidence do we still need before assessing the quality problem?",
                    required_evidence_ids={"process-observation", "approved-procedure"},
                    capability_admission="unknown",
                ),
            ),
            evidence=(
                EvidenceReceipt(
                    id="process-observation",
                    version="1",
                    observed_at=AT,
                    valid_until=AT + timedelta(hours=1),
                    applicable=True,
                ),
            ),
            selected_evidence_ids={"process-observation"},
        )

    def authenticated_principal(self):
        return HostPrincipal("synthetic-professional", "synthetic", frozenset({"reader"}))

    def load_authorized_snapshot(self, work_id, principal):
        return self.snapshot


def walkthrough():
    host = SyntheticHost()

    def read():
        return read_work_context(
            WorkContextRequest(
                work_id=host.snapshot.work_id, expected_revision=host.snapshot.revision
            ),
            host,
            at=AT,
        ).model_dump(mode="json")

    missing = read()
    procedure = EvidenceReceipt(
        id="approved-procedure",
        version="1",
        observed_at=AT,
        valid_until=AT + timedelta(days=1),
        applicable=True,
    )
    host.snapshot = host.snapshot.model_copy(
        update={
            "revision": 2,
            "evidence": (*host.snapshot.evidence, procedure),
            "selected_evidence_ids": frozenset({"process-observation", "approved-procedure"}),
        }
    )
    current = read()
    host.snapshot = host.snapshot.model_copy(
        update={
            "revision": 3,
            "evidence": (
                host.snapshot.evidence[0],
                procedure.model_copy(update={"version": "2", "conflict": True}),
            ),
        }
    )
    changed = read()
    return {
        "qualification": "synthetic contract walkthrough; no live authorization or diagnosis",
        "missing": missing,
        "current": current,
        "changed": changed,
    }


if __name__ == "__main__":
    print(json.dumps(walkthrough(), sort_keys=True, indent=2))
