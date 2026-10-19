"""Provider-neutral evidence projection for the Drilling NPT Industry IQ pack.

This module is deliberately domain-specific but provider-neutral. Platform bindings
resolve authoritative evidence into this thin projection; the existing Drilling NPT
Industry IQ pack remains the owner of NPT reasoning. Provider schemas and transport
concerns stay outside CEPIO Core.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field, StrictBool

from .bootstrap import build_runtime
from .domain_bindings import ExternalRecordReference
from .drilling_npt_iq import DRILLING_NPT_IQ_PACK, NPTDurationAssessment
from .industry_iq import install_industry_iq_packs
from .model import ObjectRef, OntologyObject, Relationship
from .platform_bindings import EvidenceBinding, qualify_evidence_binding
from .runtime import CEPIORuntime


class DrillingNPTActivityEvidence(BaseModel):
    activity_id: str
    activity_name: str
    start_time: str
    end_time: str
    classification_id: str
    classification_name: str
    is_productive: StrictBool
    activity_reference: ExternalRecordReference
    classification_reference: ExternalRecordReference


class DrillingNPTContextEvidence(BaseModel):
    context_id: str
    context_reference: ExternalRecordReference
    rig_id: str
    rig_name: str
    rig_reference: ExternalRecordReference
    well_id: str
    well_name: str
    well_reference: ExternalRecordReference
    activities: list[DrillingNPTActivityEvidence] = Field(min_length=1)

    @property
    def references(self) -> list[ExternalRecordReference]:
        refs = [self.context_reference, self.rig_reference, self.well_reference]
        for activity in self.activities:
            refs.extend([activity.activity_reference, activity.classification_reference])
        return refs


class DrillingNPTBindingQualification(BaseModel):
    binding_id: str
    source_system: str
    context_id: str
    semantic_signature: str
    assessment: NPTDurationAssessment
    evidence_references: list[ExternalRecordReference]


def _materialize_context(runtime: CEPIORuntime, context: DrillingNPTContextEvidence) -> None:
    runtime.upsert_object(
        OntologyObject(id=context.rig_id, type="OperatingRig", name=context.rig_name)
    )
    runtime.upsert_object(OntologyObject(id=context.well_id, type="Well", name=context.well_name))

    for item in context.activities:
        runtime.upsert_object(
            OntologyObject(
                id=item.activity_id,
                type="ActivityInterval",
                name=item.activity_name,
                properties={"startTime": item.start_time, "endTime": item.end_time},
            )
        )
        runtime.upsert_object(
            OntologyObject(
                id=item.classification_id,
                type="DrillingActivityClassification",
                name=item.classification_name,
                properties={"isProductive": item.is_productive},
            )
        )
        runtime.add_relationship(
            Relationship(
                type="activityOnRig",
                source=ObjectRef(id=item.activity_id, type="ActivityInterval"),
                target=ObjectRef(id=context.rig_id, type="OperatingRig"),
            )
        )
        runtime.add_relationship(
            Relationship(
                type="activityForWell",
                source=ObjectRef(id=item.activity_id, type="ActivityInterval"),
                target=ObjectRef(id=context.well_id, type="Well"),
            )
        )
        runtime.add_relationship(
            Relationship(
                type="classifiedBy",
                source=ObjectRef(id=item.activity_id, type="ActivityInterval"),
                target=ObjectRef(
                    id=item.classification_id,
                    type="DrillingActivityClassification",
                ),
            )
        )


def _validate_provenance(binding: EvidenceBinding, context: DrillingNPTContextEvidence) -> None:
    source_system = binding.manifest.source_system
    for reference in context.references:
        if reference.source_system != source_system:
            raise ValueError(
                "Drilling NPT evidence source_system does not match binding manifest: "
                f"{reference.source_system!r} != {source_system!r}"
            )
        if reference.record_version is None:
            raise ValueError(
                f"Drilling NPT evidence reference {reference.stable_key!r} has no record_version"
            )


def _semantic_signature(
    context: DrillingNPTContextEvidence,
    assessment: NPTDurationAssessment,
) -> str:
    payload: dict[str, Any] = {
        "rig_id": context.rig_id,
        "well_id": context.well_id,
        "activities": sorted(
            [
                {
                    "activity_id": item.activity_id,
                    "start_time": item.start_time,
                    "end_time": item.end_time,
                    "classification_id": item.classification_id,
                    "is_productive": item.is_productive,
                }
                for item in context.activities
            ],
            key=lambda item: item["activity_id"],
        ),
        "assessment": assessment.model_dump(mode="json"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def qualify_drilling_npt_binding(
    binding: EvidenceBinding,
    *,
    external_id: str,
) -> DrillingNPTBindingQualification:
    """Run the same Drilling NPT Industry IQ against one evidence binding.

    The generic binding contract is qualified first. The binding then resolves a thin
    domain evidence projection, which is materialized only into an ephemeral CEPIO
    runtime. Source identity/version provenance remains attached to the qualification
    result and is deliberately excluded from the semantic parity hash.
    """

    qualify_evidence_binding(binding, external_id=external_id)
    envelope = binding.resolve_evidence(external_id)
    context = DrillingNPTContextEvidence.model_validate(envelope.evidence)
    if context.context_id != external_id:
        raise ValueError(
            f"Drilling NPT context identity changed: {context.context_id!r} != {external_id!r}"
        )
    if context.context_reference.stable_key != envelope.reference.stable_key:
        raise ValueError("Envelope reference does not match the drilling context reference")
    _validate_provenance(binding, context)

    runtime = build_runtime()
    install_industry_iq_packs(runtime, [DRILLING_NPT_IQ_PACK])
    _materialize_context(runtime, context)
    assessment = runtime.call_function(
        "calculateNPTDuration",
        rig_id=context.rig_id,
        well_id=context.well_id,
        activity_ids=[item.activity_id for item in context.activities],
    )

    return DrillingNPTBindingQualification(
        binding_id=binding.manifest.binding_id,
        source_system=binding.manifest.source_system,
        context_id=context.context_id,
        semantic_signature=_semantic_signature(context, assessment),
        assessment=assessment,
        evidence_references=context.references,
    )
