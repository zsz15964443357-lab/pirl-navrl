#!/usr/bin/env python3
"""Run a TASK_04 diagnostic rollout on real gym-pybullet-drones."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.evaluation.rollout_recorder import (  # noqa: E402
    RolloutInitialStateRecord,
    RolloutJsonlWriter,
    RolloutStepRecord,
    RolloutSummary,
)
from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv  # noqa: E402
from pirl_navrl.policies.simple_policies import GoalSeekingVelocityPolicy  # noqa: E402
from pirl_navrl.scenarios.core import make_scenario  # noqa: E402


DEFAULT_CONFIG_PATH = ROOT_DIR / "configs/task04_gym_pybullet_static_nav_debug.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--gui", action="store_true", help="Show the live gym-pybullet-drones GUI during rollout.")
    parser.add_argument("--replay-gui", action="store_true", help="Open the trace replay viewer after rollout.")
    parser.add_argument("--start", nargs=3, type=float, metavar=("X", "Y", "Z"))
    parser.add_argument("--goal", nargs=3, type=float, metavar=("X", "Y", "Z"))
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--max-speed", type=float)
    parser.add_argument(
        "--camera-mode",
        choices=("fixed", "follow", "manual"),
        default="manual",
        help="manual allows camera control; follow recenters every step.",
    )
    parser.add_argument(
        "--camera-control",
        choices=("orbit", "pybullet"),
        default="orbit",
        help="orbit uses TASK_04 mouse camera controls; pybullet uses PyBullet's raw GUI bindings.",
    )
    parser.add_argument(
        "--enable-mouse-picking",
        action="store_true",
        help="Allow PyBullet mouse picking in --camera-control pybullet mode; this lets left mouse drag dynamic bodies.",
    )
    parser.add_argument("--show-pybullet-ui", action="store_true")
    parser.add_argument("--show-camera-preview", action="store_true")
    parser.add_argument("--show-drone-marker", action="store_true")
    parser.add_argument(
        "--onboard-camera",
        action="store_true",
        help="Sample a lightweight drone-facing-goal camera and write camera stats to JSONL.",
    )
    parser.add_argument(
        "--onboard-camera-size",
        nargs=2,
        type=int,
        default=(640, 480),
        metavar=("WIDTH", "HEIGHT"),
        help="Resolution for the lightweight onboard camera hook.",
    )
    parser.add_argument(
        "--onboard-camera-period",
        type=int,
        default=4,
        help="Sample the lightweight onboard camera every N control steps.",
    )
    parser.add_argument(
        "--clean-visuals",
        action="store_true",
        help="Replace the default PyBullet checkerboard plane with a cleaner diagnostic grid.",
    )
    parser.add_argument("--realtime", action="store_true", help="Sleep between steps at the control rate.")
    parser.add_argument(
        "--hold-seconds",
        type=float,
        help="Seconds to keep the live GUI open after rollout. Omit this in --gui mode to keep it open.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_scenario_overrides(scenario, args: argparse.Namespace):
    updates: dict[str, Any] = {}
    if args.start is not None:
        updates["start"] = tuple(float(value) for value in args.start)
    if args.goal is not None:
        updates["goal"] = tuple(float(value) for value in args.goal)
    if args.max_steps is not None:
        updates["max_steps"] = int(args.max_steps)
    return replace(scenario, **updates) if updates else scenario


def wait_for_live_gui(env: Task04GymPybulletDronesRLEnv) -> None:
    try:
        import pybullet as p
    except ImportError:
        return
    client = None
    if env.adapter is not None:
        client = env.adapter.pybullet_client
    if client is None:
        return
    print("[info] Live PyBullet GUI is being held open. Close the window or press Ctrl+C to exit.")
    try:
        while p.isConnected(client):
            time.sleep(1.0 / 30.0)
    except KeyboardInterrupt:
        pass


def write_initial(writer: RolloutJsonlWriter, env: Task04GymPybulletDronesRLEnv, info: dict[str, Any]) -> None:
    writer.write_initial_state(
        RolloutInitialStateRecord(
            task_id="TASK_04",
            output_type="diagnostic",
            platform_id=info["platform_id"],
            scenario_id=info["scenario_id"],
            seed=int(info["seed"]),
            policy_id="goal_seeking_velocity_debug",
            step=0,
            position=tuple(info["position"]),
            velocity=tuple(info["velocity"]),
            goal=env.scenario.goal,
            distance_to_goal=float(info["distance_to_goal"]),
            min_clearance=float(info["min_clearance"]),
            collision=bool(info["collision"]),
            success=bool(info["success"]),
            timeout=bool(info["timeout"]),
        )
    )


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.output is not None:
        config["output_path"] = str(args.output)
    if args.gui:
        config["live_gui"] = True
        if args.max_steps is None:
            args.max_steps = 3000
        if args.goal is None:
            args.goal = (3.0, 2.0, 1.0)
        print(
            "[info] GUI camera control: orbit mode uses left/right drag to rotate and middle drag/wheel to zoom. "
            "Mouse picking is off by default so left drag does not grab the drone."
        )
    if args.replay_gui:
        config["replay_gui"] = True
    if args.max_speed is not None:
        config["max_speed"] = float(args.max_speed)
    scenario = apply_scenario_overrides(
        make_scenario(config["scenario_id"], seed=int(config["seed"])),
        args,
    )
    output_path = Path(config["output_path"])
    if not output_path.is_absolute():
        output_path = ROOT_DIR / output_path

    env = Task04GymPybulletDronesRLEnv(
        scenario=scenario,
        max_speed=float(config["max_speed"]),
        gui=bool(config.get("live_gui")),
        camera_mode=args.camera_mode,
        camera_control=args.camera_control,
        enable_mouse_picking=args.enable_mouse_picking,
        show_pybullet_ui=args.show_pybullet_ui,
        show_camera_preview=args.show_camera_preview,
        show_drone_marker=args.show_drone_marker,
        enable_onboard_camera=args.onboard_camera,
        onboard_camera_width=int(args.onboard_camera_size[0]),
        onboard_camera_height=int(args.onboard_camera_size[1]),
        onboard_camera_period=int(args.onboard_camera_period),
        clean_visuals=bool(args.clean_visuals),
    )
    policy = GoalSeekingVelocityPolicy(max_speed=float(config["max_speed"]))
    policy.reset(scenario)

    obs, info = env.reset(seed=scenario.seed)
    del obs
    min_clearance = float(info["min_clearance"])
    last_info = info
    metadata = {
        "task_id": "TASK_04",
        "output_type": "diagnostic",
        "platform_id": config["platform_id"],
        "scenario_id": scenario.scenario_id,
        "seed": scenario.seed,
        "policy_id": policy.policy_id,
        "scenario": scenario.to_dict(),
        "custom_obstacles_physical": True,
    }

    try:
        with RolloutJsonlWriter(output_path, metadata) as writer:
            write_initial(writer, env, info)
            for step_index in range(scenario.max_steps):
                observation = {
                    "position": last_info["position"],
                    "velocity": last_info["velocity"],
                    "goal": scenario.goal,
                }
                desired_velocity = policy.act(observation)
                normalized_action = [float(value) / float(config["max_speed"]) for value in desired_velocity]
                flattened_obs, reward, terminated, truncated, info = env.step(normalized_action)
                del flattened_obs, reward
                min_clearance = min(min_clearance, float(info["min_clearance"]))
                writer.write_step(
                    RolloutStepRecord(
                        task_id="TASK_04",
                        output_type="diagnostic",
                        platform_id=info["platform_id"],
                        scenario_id=info["scenario_id"],
                        seed=int(info["seed"]),
                        policy_id=policy.policy_id,
                        step=step_index + 1,
                        position=tuple(info["position"]),
                        velocity=tuple(info["velocity"]),
                        goal=scenario.goal,
                        action=tuple(info["applied_action"]),
                        distance_to_goal=float(info["distance_to_goal"]),
                        min_clearance=float(info["min_clearance"]),
                        collision=bool(info["collision"]),
                        success=bool(info["success"]),
                        timeout=bool(info["timeout"]),
                        safety_collision=bool(info["safety_collision"]),
                        physical_collision=bool(info["physical_collision"]),
                        custom_obstacles_physical=bool(info["custom_obstacles_physical"]),
                        obstacle_body_ids=dict(info["obstacle_body_ids"]),
                        platform_terminated=bool(info["platform_terminated"]),
                        platform_truncated=bool(info["platform_truncated"]),
                        onboard_camera=dict(info["onboard_camera"]),
                    )
                )
                last_info = info
                if terminated or truncated:
                    break
                if args.realtime or config.get("live_gui"):
                    time.sleep(1.0 / 48.0)

            summary = RolloutSummary(
                task_id="TASK_04",
                output_type="diagnostic",
                platform_id=config["platform_id"],
                scenario_id=scenario.scenario_id,
                seed=scenario.seed,
                policy_id=policy.policy_id,
                steps=int(last_info.get("step", step_index + 1)),
                final_distance_to_goal=float(last_info["distance_to_goal"]),
                min_clearance=float(min_clearance),
                collision=bool(last_info["collision"]),
                success=bool(last_info["success"]),
                timeout=bool(last_info["timeout"]),
            )
            writer.write_summary(summary)
    finally:
        if config.get("live_gui"):
            if args.hold_seconds is None:
                wait_for_live_gui(env)
            elif args.hold_seconds > 0.0:
                time.sleep(args.hold_seconds)
        env.close()

    print(json.dumps(summary.__dict__, indent=2, sort_keys=True))
    if config.get("replay_gui"):
        subprocess.run(
            [sys.executable, str(ROOT_DIR / "scripts/view_task03_rollout.py"), "--trace", str(output_path)],
            check=True,
        )


if __name__ == "__main__":
    main()
