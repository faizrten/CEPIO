from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


BindingTreatment = Literal["REUSE", "BIND", "EXTEND", "OWN"]


class ExternalRecordReference(BaseModel):
    """Immutable reference to an authoritative record owned by an external domain system.

    CEPIO uses this contract to preserve external identity and version provenance without
    importing the provider's full schema or bulk payload into canonical CEPIO state.
    """

    model_config = ConfigDict(frozen=True)

    source_system: str
    record_kind: str
    record_id: str
    source_service: str | None = None
    record_version: str | int | None = None
    partition: str | None = None
    dataset_id: str | None = None
    source_uri: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def stable_key(self) -> str:
        parts = [self.source_system, self.record_kind, self.record_id]
        if self.record_version is not None:
            parts.append(str(self.record_version))
        return ":".join(parts)


class DomainObjectBinding(BaseModel):
    id: str
    external_kind: str
    provider_capability: str
    treatment: BindingTreatment
    storage_policy: str
    provider_service: str | None = Field(default=None, validation_alias="adme_service")
    cepio_type: str | None = None
    reasoning_roles: list[str] = Field(default_factory=list)
    sidecar_semantics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_treatment_contract(self) -> "DomainObjectBinding":
        if self.treatment == "BIND" and not self.cepio_type:
            raise ValueError("BIND object requires cepio_type")
        if self.treatment == "EXTEND" and not self.sidecar_semantics:
            raise ValueError("EXTEND object requires sidecar_semantics")
        return self


class RuntimeCapabilityBinding(BaseModel):
    preferred_binding: str | None = None
    fallback_strategy: str | None = None
    note: str | None = None


class DomainBindingContract(BaseModel):
    """Source-neutral runtime view of a domain federation/binding manifest."""

    schema_version: str
    profile: str
    status: str | None = None
    baseline: dict[str, str] = Field(default_factory=dict)
    principles: dict[str, Any] = Field(default_factory=dict)
    providers: dict[str, Any] = Field(default_factory=dict)
    objects: list[DomainObjectBinding] = Field(default_factory=list)
    cepio_native: list[dict[str, Any]] = Field(default_factory=list)
    runtime_capabilities: dict[str, RuntimeCapabilityBinding] = Field(default_factory=dict)
    anti_duplication_invariants: list[str] = Field(default_factory=list)

    @classmethod
    def load_yaml(cls, path: str | Path) -> "DomainBindingContract":
        payload: Any = yaml.safe_load(Path(path).read_text())
        return cls.model_validate(payload)

    def object_binding(self, binding_id: str) -> DomainObjectBinding:
        matches = [item for item in self.objects if item.id == binding_id]
        if not matches:
            raise KeyError(f"Unknown domain object binding: {binding_id}")
        if len(matches) > 1:
            raise ValueError(f"Duplicate domain object binding: {binding_id}")
        return matches[0]

    def capability(self, capability_id: str) -> RuntimeCapabilityBinding:
        try:
            return self.runtime_capabilities[capability_id]
        except KeyError as exc:
            raise KeyError(f"Unknown domain capability: {capability_id}") from exc

    def resolve_preferred_binding(self, capability_id: str) -> str | None:
        return self.capability(capability_id).preferred_binding
