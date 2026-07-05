"""Render TASK_06 JSONL cases to GIF or fallback summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pirl_navrl.analysis.rollout_metrics import compute_rollout_metrics, load_jsonl_records


def render_task06_case_gif(trace_path: str | Path, output_path: str | Path, *, max_frames: int = 120) -> Path:
    trace = Path(trace_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        fallback = output.with_suffix(".fallback_summary.json")
        fallback.write_text(
            json.dumps(
                {
                    "task_id": "TASK_06",
                    "output_type": "diagnostic_gif_fallback",
                    "trace_path": str(trace),
                    "requested_gif": str(output),
                    "reason": f"missing optional dependency: {type(exc).__name__}",
                    "metrics": compute_rollout_metrics(trace),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return fallback
    try:
        import imageio.v2 as imageio
    except ImportError:
        imageio = None
    records = load_jsonl_records(trace)
    metadata = next((record for record in records if record.get("record_type") == "metadata"), {})
    scenario = metadata.get("scenario", {})
    steps = [record for record in records if record.get("record_type") in {"initial_state", "step"}]
    if max_frames > 0 and len(steps) > max_frames:
        indices = np.linspace(0, len(steps) - 1, num=max_frames, dtype=int)
        steps = [steps[int(index)] for index in indices]
    frames: list[Any] = []
    positions: list[list[float]] = []
    for index, step in enumerate(steps):
        positions.append(step["position"])
        fig, ax = plt.subplots(figsize=(5, 5))
        status = "success" if step.get("success") else "collision" if step.get("collision") else "timeout" if step.get("timeout") else "running"
        ax.set_title(
            f"TASK_06 step={step.get('step', index)} dist={step.get('distance_to_goal', 0):.2f} "
            f"clear={step.get('min_clearance', 0):.2f} {status}"
        )
        ax.set_xlim((scenario.get("bounds", {}).get("x") or [-5, 5]))
        ax.set_ylim((scenario.get("bounds", {}).get("y") or [-5, 5]))
        ax.set_aspect("equal", adjustable="box")
        _draw_scenario(ax, scenario, step)
        points = np.asarray(positions, dtype=float)
        ax.plot(points[:, 0], points[:, 1], color="orange", linewidth=2)
        ax.scatter([points[-1, 0]], [points[-1, 1]], color="orange", s=50)
        fig.canvas.draw()
        image = np.asarray(fig.canvas.buffer_rgba(), dtype="uint8")[:, :, :3].copy()
        frames.append(image)
        plt.close(fig)
    if not frames:
        raise ValueError(f"trace {trace} contains no drawable records")
    if imageio is not None:
        imageio.mimsave(output, frames, duration=0.08)
    else:
        from PIL import Image

        pil_frames = [Image.fromarray(frame) for frame in frames]
        pil_frames[0].save(
            output,
            save_all=True,
            append_images=pil_frames[1:],
            duration=80,
            loop=0,
        )
    return output


def _draw_scenario(ax: Any, scenario: dict[str, Any], step: dict[str, Any]) -> None:
    import matplotlib.patches as patches

    start = scenario.get("start")
    goal = scenario.get("goal")
    if start:
        ax.scatter([start[0]], [start[1]], color="blue", s=60, label="start")
    if goal:
        ax.scatter([goal[0]], [goal[1]], color="green", s=80, label="goal")
    for obstacle in scenario.get("static_obstacles", []):
        ax.add_patch(patches.Circle(obstacle["position"][:2], obstacle["radius"], color="red", alpha=0.45))
    dynamic_positions = step.get("dynamic_obstacle_positions") or []
    dynamic_obstacles = scenario.get("dynamic_obstacles", [])
    for index, obstacle in enumerate(dynamic_obstacles):
        initial_position = obstacle["position"]
        if initial_position:
            ax.add_patch(patches.Circle(initial_position[:2], obstacle["radius"], color="purple", alpha=0.14))
        position = dynamic_positions[index] if index < len(dynamic_positions) else initial_position
        ax.add_patch(patches.Circle(position[:2], obstacle["radius"], color="purple", alpha=0.6))
        if float(obstacle.get("start_time", 0.0)) > 0.0:
            ax.scatter([position[0]], [position[1]], color="black", marker="x", s=40)
