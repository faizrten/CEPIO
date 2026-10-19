from importlib.metadata import entry_points


def test_management_console_entrypoint_is_packaged() -> None:
    matches = [
        entry_point
        for entry_point in entry_points(group="console_scripts")
        if entry_point.name == "cepio-management"
    ]

    assert len(matches) == 1
    assert matches[0].value == "cepio.management_api:main"
