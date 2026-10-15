from __future__ import annotations

from datetime import datetime
from typing import Any

from cepio.model import OntologyObject, Relationship
from cepio.property_registry import PropertyRegistry, UnknownPropertyError
from cepio.provenance import PropertyProvenance, ProvenanceRepository, explain_property
from cepio.query import ObjectQuery, ObjectQueryResult, QueryEngine
from cepio.runtime import CEPIORuntime


class ContractAwareCEPIORuntime(CEPIORuntime):
    """CEPIO runtime with IRI-first datatype-property and temporal semantics.

    Existing v0.2 payloads may still contain legacy/unregistered property keys while
    CEPIO migrates. Canonical property APIs always resolve through PropertyRegistry.
    Set ``strict_properties=True`` to require and persist canonical property IRIs on
    object upsert.
    """

    def __init__(
        self,
        *args: Any,
        property_registry: PropertyRegistry | None = None,
        provenance_repository: ProvenanceRepository | None = None,
        strict_properties: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.property_registry = property_registry
        self.provenance_repository = provenance_repository
        self.strict_properties = strict_properties

    def upsert_object(self, obj: OntologyObject, expected_version: int | None = None) -> OntologyObject:
        if self.property_registry and self.strict_properties:
            normalized: dict[str, Any] = {}
            for key, value in obj.properties.items():
                try:
                    canonical = self.property_registry.resolve(key).iri
                except UnknownPropertyError as exc:
                    raise ValueError(f"Undeclared CEPIO datatype property: {key}") from exc
                normalized[canonical] = value
            obj = obj.model_copy(update={"properties": normalized})
        return super().upsert_object(obj, expected_version=expected_version)

    def get_property(self, object_id: str, property_name: str) -> Any:
        if not self.property_registry:
            return self.get_object(object_id).properties[property_name]
        definition = self.property_registry.resolve(property_name)
        obj = self.get_object(object_id)
        if definition.iri in obj.properties:
            return obj.properties[definition.iri]
        for alias in (definition.qname, definition.local_name):
            if alias in obj.properties:
                return obj.properties[alias]
        raise KeyError(f"Object {object_id} has no value for canonical property {definition.iri}")

    def set_property(
        self,
        object_id: str,
        property_name: str,
        value: Any,
        *,
        expected_version: int | None = None,
        provenance: PropertyProvenance | None = None,
    ) -> OntologyObject:
        if not self.property_registry:
            raise RuntimeError("Canonical property registry is not configured")
        definition = self.property_registry.resolve(property_name)
        obj = self.get_object(object_id)
        properties = dict(obj.properties)
        properties[definition.iri] = value
        properties.pop(definition.qname, None)
        properties.pop(definition.local_name, None)
        updated = obj.model_copy(update={"properties": properties})
        stored = super().upsert_object(
            updated,
            expected_version=obj.version if expected_version is None else expected_version,
        )
        if provenance:
            if not self.provenance_repository:
                raise RuntimeError("Provenance repository is not configured")
            if provenance.object_id != object_id:
                raise ValueError("Property provenance object_id does not match target object")
            if provenance.property_iri != definition.iri:
                raise ValueError("Property provenance IRI does not match canonical property")
            self.provenance_repository.append_property(provenance)
        return stored

    def explain_property(self, object_id: str, property_name: str) -> dict[str, Any]:
        if not self.property_registry or not self.provenance_repository:
            raise RuntimeError("Property registry and provenance repository are required")
        return explain_property(
            object_id,
            property_name,
            self.property_registry,
            self.provenance_repository,
        )

    def query_objects(self, query: ObjectQuery) -> ObjectQueryResult:
        """Execute the stable typed CEPIO object-set query contract."""
        return QueryEngine(self).execute(query)

    def query_objects_for_actor(self, query: ObjectQuery, roles: set[str]) -> ObjectQueryResult:
        """Execute a typed query with actor visibility applied before totals/pagination."""
        return QueryEngine(self).execute(query, actor_roles=roles)

    def get_object_at(self, object_id: str, transaction_time: datetime) -> OntologyObject:
        method = getattr(self.object_repository, "get_object_at", None)
        if method is None:
            raise RuntimeError("Configured repository does not support temporal object history")
        obj = method(object_id, transaction_time)
        if obj is None:
            raise KeyError(f"No CEPIO object {object_id} existed at transaction time {transaction_time.isoformat()}")
        return obj

    def get_object_valid_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,
        as_of_transaction: datetime | None = None,
    ) -> OntologyObject:
        method = getattr(self.object_repository, "get_object_valid_at", None)
        if method is None:
            raise RuntimeError("Configured repository does not support valid-time object history")
        obj = method(object_id, valid_time, as_of_transaction=as_of_transaction)
        if obj is None:
            raise KeyError(f"No CEPIO object {object_id} was valid at {valid_time.isoformat()}")
        return obj

    def relationships_at(
        self,
        object_id: str,
        valid_time: datetime,
        *,        direction: str = "out",
        as_of_transaction: datetime | None = None,
    ) -> list[Relationship]:
        method = getattr(self.object_repository, "relationships_at", None)
        if method is None:
            raise RuntimeError("Configured repository does not support temporal relationship history")
        return method(
            object_id,
            valid_time,
            direction=direction,
            as_of_transaction=as_of_transaction,
        )

    def object_history(self, object_id: str):
        method = getattr(self.object_repository, "object_history", None)
        if method is None:
            raise RuntimeError("Configured repository does not support object history")
        return method(object_id)

    def relationship_history(self, relationship_id: str):
        method = getattr(self.object_repository, "relationship_history", None)
        if method is None:
            raise RuntimeError("Configured repository does not support relationship history")
        return method(relationship_id)
