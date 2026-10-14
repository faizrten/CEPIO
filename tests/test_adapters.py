from cepio.adapters import (
    AVEVAPIAdapter,
    FabricOneLakeAdapter,
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
