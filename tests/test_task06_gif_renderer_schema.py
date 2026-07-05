import json

from pirl_navrl.visualization.gif_renderer import render_task06_case_gif


def test_task06_gif_renderer_outputs_gif_or_fallback(tmp_path) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "record_type": "metadata",
                    "scenario": {
                        "start": [0, 0, 1],
                        "goal": [1, 0, 1],
                        "bounds": {"x": [-1, 2], "y": [-1, 1], "z": [0, 2]},
                        "static_obstacles": [],
                        "dynamic_obstacles": [],
                    },
                },
                {"record_type": "initial_state", "step": 0, "position": [0, 0, 1], "distance_to_goal": 1.0},
                {"record_type": "step", "step": 1, "position": [0.5, 0, 1], "distance_to_goal": 0.5, "min_clearance": 1.0},
                {
                    "record_type": "summary",
                    "steps": 1,
                    "success": False,
                    "collision": False,
                    "timeout": True,
                    "final_distance_to_goal": 0.5,
                    "min_clearance": 1.0,
                },
            ]
        ),
        encoding="utf-8",
    )

    output = render_task06_case_gif(trace, tmp_path / "case.gif")

    assert output.exists()
    assert output.suffix in {".gif", ".json"}
    if output.suffix == ".json":
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["task_id"] == "TASK_06"
        assert payload["output_type"] == "diagnostic_gif_fallback"
