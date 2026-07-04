import json

from pirl_navrl.evaluation.diagnostic_logger import DiagnosticJsonlWriter


def test_diagnostic_jsonl_preserves_task02_required_fields(tmp_path) -> None:
    path = tmp_path / "task02.jsonl"
    metadata = {
        "task_id": "TASK_02",
        "output_type": "diagnostic",
        "route": "official_ego_docker_sidecar",
        "source_launch": "pirl_navrl/bridges/ego_planner_bridge/ego_custom_map_sidecar.launch",
        "scenario_id": "ego_static_obstacle_v0",
        "obstacle_mode": "static",
        "goal": [-8.0, 10.0, 1.0],
    }

    with DiagnosticJsonlWriter(path, metadata) as writer:
        writer.write(
            {
                "record_type": "state",
                "step": 0,
                "elapsed": 0.0,
                "odom_position": [-18.0, 0.0, 0.0],
                "ego_command_position": None,
                "distance_to_goal": None,
            }
        )

    record = json.loads(path.read_text(encoding="utf-8").strip())
    for field in [
        "task_id",
        "output_type",
        "route",
        "source_launch",
        "scenario_id",
        "obstacle_mode",
        "goal",
        "record_type",
        "timestamp",
        "elapsed",
        "odom_position",
        "ego_command_position",
        "distance_to_goal",
    ]:
        assert field in record
