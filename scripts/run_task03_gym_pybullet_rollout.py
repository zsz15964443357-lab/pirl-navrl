#!/usr/bin/env python3
"""Run the TASK_03 diagnostic scenario/policy/rollout pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.evaluation.rollout_recorder import (  # noqa: E402
    RolloutJsonlWriter,
    RolloutStepRecord,
    RolloutSummary,
)
from pirl_navrl.platforms.diagnostic_kinematic_env import DiagnosticKinematicEnv  # noqa: E402
from pirl_navrl.policies.simple_policies import GoalSeekingVelocityPolicy, RandomVelocityPolicy  # noqa: E402
from pirl_navrl.scenarios.core import ScenarioConfig, make_scenario  # noqa: E402


DEFAULT_CONFIG_PATH = ROOT_DIR / "configs/task03_static_nav_debug.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--scenario", dest="scenario_id")
    parser.add_argument("--policy", dest="policy_id")
    parser.add_argument("--platform", dest="platform_id")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", dest="output_path", type=Path)
    parser.add_argument("--gui", action="store_true")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def make_policy(policy_id: str, seed: int):
    if policy_id == "goal_seeking_velocity_debug":
        return GoalSeekingVelocityPolicy(max_speed=1.0)
    if policy_id == "random_velocity_debug":
        return RandomVelocityPolicy(max_speed=0.8, seed=seed)
    raise ValueError(f"unknown TASK_03 policy_id {policy_id!r}")


def make_platform(platform_id: str) -> DiagnosticKinematicEnv:
    if platform_id != "diagnostic_kinematic_env":
        raise ValueError(
            "TASK_03 currently supports only platform_id='diagnostic_kinematic_env'. "
            "The real gym-pybullet-drones adapter is a later-task skeleton."
        )
    return DiagnosticKinematicEnv(max_speed=1.0)


def build_step_record(
    *,
    scenario: ScenarioConfig,
    platform_id: str,
    policy_id: str,
    info: dict[str, Any],
) -> RolloutStepRecord:
    return RolloutStepRecord(
        task_id="TASK_03",
        output_type="diagnostic",
        platform_id=platform_id,
        scenario_id=scenario.scenario_id,
        seed=scenario.seed,
        policy_id=policy_id,
        step=int(info["step"]),
        position=tuple(info["position"]),
        velocity=tuple(info["velocity"]),
        goal=tuple(info["goal"]),
        action=tuple(info["action"]),
        distance_to_goal=float(info["distance_to_goal"]),
        min_clearance=float(info["min_clearance"]),
        collision=bool(info["collision"]),
        success=bool(info["success"]),
        timeout=bool(info["timeout"]),
    )


def run_rollout(config: dict[str, Any]) -> RolloutSummary:
    scenario = make_scenario(config["scenario_id"], seed=int(config["seed"]))
    policy = make_policy(config["policy_id"], seed=scenario.seed)
    env = make_platform(config["platform_id"])
    output_path = Path(config["output_path"])
    if not output_path.is_absolute():
        output_path = ROOT_DIR / output_path

    observation = env.reset(scenario)
    policy.reset(scenario)
    min_clearance = env.min_clearance()
    last_info: dict[str, Any] | None = None

    metadata = {
        "platform_id": env.platform_id,
        "scenario_id": scenario.scenario_id,
        "seed": scenario.seed,
        "policy_id": policy.policy_id,
        "scenario": scenario.to_dict(),
    }
    with RolloutJsonlWriter(output_path, metadata) as writer:
        for _ in range(scenario.max_steps):
            action = policy.act(observation)
            observation, _reward, terminated, truncated, info = env.step(action)
            last_info = info
            min_clearance = min(min_clearance, float(info["min_clearance"]))
            writer.write_step(
                build_step_record(
                    scenario=scenario,
                    platform_id=env.platform_id,
                    policy_id=policy.policy_id,
                    info=info,
                )
            )
            if terminated or truncated:
                break

        if last_info is None:
            last_info = {
                "step": 0,
                "distance_to_goal": 0.0,
                "collision": False,
                "success": False,
                "timeout": True,
            }
        summary = RolloutSummary(
            task_id="TASK_03",
            output_type="diagnostic",
            platform_id=env.platform_id,
            scenario_id=scenario.scenario_id,
            seed=scenario.seed,
            policy_id=policy.policy_id,
            steps=int(last_info["step"]),
            final_distance_to_goal=float(last_info["distance_to_goal"]),
            min_clearance=float(min_clearance),
            collision=bool(last_info["collision"]),
            success=bool(last_info["success"]),
            timeout=bool(last_info["timeout"]),
        )
        writer.write_summary(summary)

    print(json.dumps(summary.__dict__, indent=2, sort_keys=True))
    return summary


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.scenario_id is not None:
        config["scenario_id"] = args.scenario_id
    if args.policy_id is not None:
        config["policy_id"] = args.policy_id
    if args.platform_id is not None:
        config["platform_id"] = args.platform_id
    if args.seed is not None:
        config["seed"] = args.seed
    if args.output_path is not None:
        config["output_path"] = str(args.output_path)
    if args.gui:
        config["visualize"] = True

    run_rollout(config)

    if config.get("visualize"):
        trace_path = Path(config["output_path"])
        if not trace_path.is_absolute():
            trace_path = ROOT_DIR / trace_path
        subprocess.run(
            [sys.executable, str(ROOT_DIR / "scripts/view_task03_rollout.py"), "--trace", str(trace_path)],
            check=True,
        )


if __name__ == "__main__":
    main()
