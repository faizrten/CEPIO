from cepio.adapters import (
    AVEVAPIAdapter,
    AdapterVerificationStatus,
    FabricOneLakeAdapter,
    GovernedVerificationRequest,
    GovernedWriteRequest,
    OSDUAdapter,
    PrimaveraP6Adapter,
    SAPS4HANAAdapter,
)


def test_reference_adapters_are_dry_run_only():
    for adapter in [
        SAPS4HANAAdapter(),
        AVEVAPIAdapter(),
        OSDUAdapter(),
        PrimaveraP6Adapter(),
        FabricOneLakeAdapter(),
    ]:
        result = adapter.write("test", {"id": "X"})
        assert result.dry_run is True
        assert result.accepted is True


def test_reference_adapters_implement_governed_write_verify_contract():
    adapter = SAPS4HANAAdapter()
    request = GovernedWriteRequest(
        execution_id="ext-1",
        system=adapter.system_name,
        operation="update_equipment",
        external_id="EQ-1",
        canonical_object_id="K-201",
        action_id="action-1",
        actor_id="engineer-1",
        idempotency_key="external:sap:update:action-1",
        payload={"status": "critical"},
    )
    receipt = adapter.write_governed(request)
    assert receipt.accepted is True
    assert receipt.source_request_id is not None

    verification = adapter.verify_write(
        GovernedVerificationRequest(
            execution_id="ext-1",
            system=adapter.system_name,
            operation="update_equipment",
            external_id="EQ-1",
            canonical_object_id="K-201",
            action_id="action-1",
            idempotency_key="external:sap:update:action-1",
            source_request_id=receipt.source_request_id,
            expected_payload={"status": "critical"},
        )
    )
    assert verification.status == AdapterVerificationStatus.verified
