import pytest

from react_m.experiments import compare, run_case


@pytest.mark.parametrize("mode, calls", [("single", 3), ("parallel", 3), ("multi", 2)])
async def test_dependency_demo_uses_results_and_labels_scripted_decisions(mode, calls):
    result = await run_case("dependency", mode, tool_delay=0, decision_delay=0)
    assert result["answer"] == "1892"
    assert result["success"] is True
    assert result["decision_calls"] == calls
    assert result["model_calls"] == 0
    assert result["tool_attempts"] == 2


async def test_comparison_keeps_negative_controls_and_all_runs():
    report = await compare(repeats=1, tool_delay=0, decision_delay=0)
    assert report["kind"] == "scripted-mechanics"
    assert len(report["runs"]) == 12
    assert all(run["success"] for run in report["runs"])
    assert {run["scenario"] for run in report["runs"]} == {
        "independent",
        "dependency",
        "ambiguous",
        "failure",
    }
