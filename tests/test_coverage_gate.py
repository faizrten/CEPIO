from scripts.check_coverage import FileCoverage, Hunk, evaluate


def totals(statements, covered, percent=None):
    if percent is None:
        percent = 100.0 if statements == 0 else 100.0 * covered / statements
    return {
        "num_statements": statements,
        "covered_lines": covered,
        "uncovered_lines": statements - covered,
        "percent_covered": percent,
    }


def test_deleting_fully_covered_code_does_not_fail_on_percentage_mix_effect():
    base_files = {
        "src/cepio/keep.py": FileCoverage(frozenset({1, 2, 3}), frozenset({4})),
        "src/cepio/delete.py": FileCoverage(frozenset({1, 2}), frozenset()),
    }
    head_files = {
        "src/cepio/keep.py": FileCoverage(frozenset({1, 2, 3}), frozenset({4})),
    }
    result = evaluate(
        base_files,
        head_files,
        totals(6, 5),
        totals(4, 3),
        {"src/cepio/delete.py": [Hunk(1, 2, 0, 0)]},
        90.0,
    )
    assert result["aggregate_delta_percent"] < 0
    assert result["uncovered_line_delta"] == 0
    assert result["passed"] is True


def test_new_untested_production_code_fails():
    result = evaluate(
        {},
        {"src/cepio/new.py": FileCoverage(frozenset(), frozenset({1}))},
        totals(0, 0),
        totals(1, 0),
        {"src/cepio/new.py": [Hunk(0, 0, 1, 1)]},
        90.0,
    )
    assert result["changed_line_coverage"]["percent_covered"] == 0.0
    assert result["passed"] is False


def test_well_tested_new_production_code_passes():
    result = evaluate(
        {},
        {"src/cepio/new.py": FileCoverage(frozenset({1, 2}), frozenset())},
        totals(0, 0),
        totals(2, 2),
        {"src/cepio/new.py": [Hunk(0, 0, 1, 2)]},
        90.0,
    )
    assert result["changed_line_coverage"]["percent_covered"] == 100.0
    assert result["passed"] is True


def test_removing_tests_that_uncover_unchanged_production_fails():
    base = FileCoverage(frozenset({1, 2}), frozenset())
    head = FileCoverage(frozenset({1}), frozenset({2}))
    result = evaluate(
        {"src/cepio/stable.py": base},
        {"src/cepio/stable.py": head},
        totals(2, 2),
        totals(2, 1),
        {},
        90.0,
    )
    assert result["unchanged_file_regressions"]["src/cepio/stable.py"]["new_uncovered_lines"] == 1
    assert result["passed"] is False


def test_changed_line_threshold_is_enforced_even_without_aggregate_debt_growth():
    base = FileCoverage(frozenset({1}), frozenset({2}))
    head = FileCoverage(frozenset({1, 3}), frozenset({2, 4}))
    result = evaluate(
        {"src/cepio/change.py": base},
        {"src/cepio/change.py": head},
        totals(2, 1),
        totals(4, 2),
        {"src/cepio/change.py": [Hunk(2, 0, 3, 2)]},
        90.0,
    )
    assert result["uncovered_line_delta"] == 1
    assert result["changed_line_coverage"]["percent_covered"] == 50.0
    assert result["passed"] is False
