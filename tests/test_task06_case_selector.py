import json

from pirl_navrl.evaluation.case_selector import select_task06_cases


def _trace(path, *, success, collision, timeout, final_distance, min_clearance=1.0):
    rows = [
        {"record_type": "metadata", "scenario": {"collision_radius": 0.35}},
        {"record_type": "step", "position": [0, 0, 1], "action": [0, 0, 0]},
        {
            "record_type": "summary",
            "steps": 1,
            "success": success,
            "collision": collision,
            "timeout": timeout,
            "final_distance_to_goal": final_distance,
            "min_clearance": min_clearance,
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_task06_case_selector_prefers_success(tmp_path) -> None:
    bad = tmp_path / "bad.jsonl"
    good = tmp_path / "good.jsonl"
    _trace(bad, success=False, collision=False, timeout=True, final_distance=0.9)
    _trace(good, success=True, collision=False, timeout=False, final_distance=0.3)

    selected = select_task06_cases([bad, good])

    assert selected["case_type"] == "success_case"
    assert selected["best_case"]["trace_path"].endswith("good.jsonl")
    assert selected["failure_case"]["failure_type"] == "timeout_failure"


def test_task06_case_selector_best_non_success_when_no_success(tmp_path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _trace(first, success=False, collision=False, timeout=True, final_distance=1.0)
    _trace(second, success=False, collision=True, timeout=False, final_distance=0.2)

    selected = select_task06_cases([first, second])

    assert selected["case_type"] == "best_non_success_case"
    assert selected["reason"] == "no_success_found"
    assert selected["best_case"]["trace_path"].endswith("first.jsonl")
    assert selected["failure_case"]["failure_type"] == "collision_failure"


def test_task06_case_selector_rejects_too_close_success(tmp_path) -> None:
    close = tmp_path / "close.jsonl"
    clean = tmp_path / "clean.jsonl"
    _trace(close, success=True, collision=False, timeout=False, final_distance=0.2, min_clearance=0.32)
    _trace(clean, success=True, collision=False, timeout=False, final_distance=0.3, min_clearance=0.5)

    selected = select_task06_cases([close, clean])

    assert selected["case_type"] == "success_case"
    assert selected["best_case"]["trace_path"].endswith("clean.jsonl")
