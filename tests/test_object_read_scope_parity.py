import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext, SkillExecutionHost
from cepio.contract_runtime import ContractAwareCEPIORuntime
from cepio.model import OntologyObject
from cepio.policy import RolePolicyEngine
from cepio.registry import TypeRegistry
from cepio.runtime import AuthorizationError, CEPIORuntime

TYPE = "urn:test:Evidence"


@pytest.fixture(params=[CEPIORuntime, ContractAwareCEPIORuntime])
def runtime(request):
    policy = RolePolicyEngine(
        {
            "reader": {
                "read_types": [TYPE],
                "read_scopes": ["internal"],
                "read_properties": {TYPE: ["visible"]},
            }
        }
    )
    runtime = request.param(
        type_registry=TypeRegistry(object_type_ids={TYPE}), policy_engine=policy
    )
    runtime.upsert_object(
        OntologyObject(
            id="E-1",
            name="Synthetic evidence",
            type=TYPE,
            properties={"sharingScope": "internal", "visible": 7, "secret": 9},
        )
    )
    return runtime


def test_allowed_scope_still_filters_properties(runtime):
    assert runtime.read_object_for_actor("E-1", {"reader"}).properties == {"visible": 7}


def test_revocation_applies_before_filtering(runtime):
    runtime.read_object_for_actor("E-1", {"reader"})
    runtime.policy_engine.policies["reader"]["read_scopes"] = ["public"]
    with pytest.raises(AuthorizationError):
        runtime.read_object_for_actor("E-1", {"reader"})


def test_type_permission_required(runtime):
    runtime.policy_engine.policies["reader"]["read_types"] = []
    with pytest.raises(AuthorizationError):
        runtime.read_object_for_actor("E-1", {"reader"})


def test_service_and_skill_host_preserve_scope_denial(runtime):
    service = CEPIOApplicationService(runtime)
    context = ExecutionContext(actor_id="reader-1", actor_roles=frozenset({"reader"}))
    host = SkillExecutionHost(service, context)
    runtime.policy_engine.policies["reader"]["read_scopes"] = []
    with pytest.raises(AuthorizationError):
        service.read_object("E-1", context)
    with pytest.raises(AuthorizationError):
        host.read_object("E-1")


def test_missing_scope_keeps_policy_semantics(runtime):
    runtime.upsert_object(
        OntologyObject(id="E-2", name="Synthetic evidence", type=TYPE, properties={"visible": 8})
    )
    assert runtime.read_object_for_actor("E-2", {"reader"}).properties == {"visible": 8}


def test_snake_case_and_multiple_scopes(runtime):
    runtime.upsert_object(
        OntologyObject(
            id="E-2",
            name="Synthetic evidence",
            type=TYPE,
            properties={"sharing_scope": ["private", "internal"]},
        )
    )
    runtime.read_object_for_actor("E-2", {"reader"})
    runtime.policy_engine.policies["reader"]["read_scopes"] = ["public"]
    with pytest.raises(AuthorizationError):
        runtime.read_object_for_actor("E-2", {"reader"})


def test_custom_object_policy_is_authoritative(runtime):
    runtime.policy_engine.can_read_object = lambda roles, obj: False
    with pytest.raises(AuthorizationError):
        runtime.read_object_for_actor("E-1", {"reader"})
