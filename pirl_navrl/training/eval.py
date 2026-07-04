"""Evaluation rollout utilities for TASK_05 debug policies."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from pirl_navrl.evaluation.rollout_recorder import (
    RolloutInitialStateRecord,
    RolloutJsonlWriter,
    RolloutStepRecord,
    RolloutSummary,
)
from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv
from pirl_navrl.scenarios.curriculum import make_curriculum_scenario

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_model(checkpoint_path: str | Path | None):
    if checkpoint_path is None:
        return None
    from stable_baselines3 import PPO

    return PPO.load(str(checkpoint_path))


def _default_output_path(curriculum_level: str, seed: int, policy_id: str) -> Path:
    return ROOT_DIR / "outputs" / "task05" / "eval" / f"{curriculum_level}_seed{seed}_{policy_id}.jsonl"


def run_task05_eval(
    *,
    checkpoint_path: str | Path | None = None,
    output_path: str | Path | None = None,
    curriculum_level: str = "level_0_no_obstacle_short",
    seed: int = 0,
    max_speed: float = 1.0,
    gui: bool = False,
    deterministic: bool = True,
    max_steps: int | None = None,
    random_policy: bool = False,
    realtime: bool = False,
    hold_seconds: float | None = None,
) -> Path:
    """Run one TASK_05 diagnostic rollout and write JSONL."""

    if checkpoint_path is not None and random_policy:
        raise ValueError("choose either checkpoint_path or random_policy, not both")
    model = None if random_policy else _load_model(checkpoint_path)
    policy_id = "random_policy_debug" if model is None else "sb3_ppo_debug_checkpoint"
    scenario = make_curriculum_scenario(curriculum_level, seed=seed)
    if max_steps is not None:
        from dataclasses import replace

        scenario = replace(scenario, max_steps=int(max_steps))
    output = Path(output_path) if output_path is not None else _default_output_path(curriculum_level, seed, policy_id)
    if not output.is_absolute():
        output = ROOT_DIR / output

    env = Task04GymPybulletDronesRLEnv(scenario=scenario, max_speed=max_speed, gui=gui)
    obs, info = env.reset(seed=seed)
    min_clearance = float(info["min_clearance"])
    last_info = info
    metadata = {
        "task_id": "TASK_05",
        "output_type": "diagnostic",
        "route": "task05_sb3_ppo_debug_eval",
        "platform_id": info["platform_id"],
        "scenario_id": scenario.scenario_id,
        "seed": scenario.seed,
        "policy_id": policy_id,
        "checkpoint_path": None if checkpoint_path is None else str(checkpoint_path),
        "curriculum_level": curriculum_level,
        "random_policy": bool(model is None),
        "scenario": scenario.to_dict(),
    }
    try:
        with RolloutJsonlWriter(output, metadata) as writer:
            writer.write_initial_state(
                RolloutInitialStateRecord(
                    task_id="TASK_05",
                    output_type="diagnostic",
                    platform_id=info["platform_id"],
                    scenario_id=info["scenario_id"],
                    seed=int(info["seed"]),
                    policy_id=policy_id,
                    step=0,
                    position=tuple(info["position"]),
                    velocity=tuple(info["velocity"]),
                    goal=scenario.goal,
                    distance_to_goal=float(info["distance_to_goal"]),
                    min_clearance=float(info["min_clearance"]),
                    collision=bool(info["collision"]),
                    success=bool(info["success"]),
                    timeout=bool(info["timeout"]),
                )
            )
            for step_index in range(scenario.max_steps):
                if model is None:
                    action = env.action_space.sample()
                else:
                    action, _state = model.predict(obs, deterministic=deterministic)
                obs, _reward, terminated, truncated, info = env.step(np.asarray(action, dtype=np.float32))
                min_clearance = min(min_clearance, float(info["min_clearance"]))
                writer.write_step(
                    RolloutStepRecord(
                        task_id="TASK_05",
                        output_type="diagnostic",
                        platform_id=info["platform_id"],
                        scenario_id=info["scenario_id"],
                        seed=int(info["seed"]),
                        policy_id=policy_id,
                        step=step_index + 1,
                        position=tuple(info["position"]),
                        velocity=tuple(info["velocity"]),
                        goal=scenario.goal,
                        action=tuple(float(value) for value in np.asarray(action, dtype=np.float32).reshape(3)),
                        distance_to_goal=float(info["distance_to_goal"]),
                        min_clearance=float(info["min_clearance"]),
                        collision=bool(info["collision"]),
                        success=bool(info["success"]),
                        timeout=bool(info["timeout"]),
                        safety_collision=bool(info.get("safety_collision", False)),
                        physical_collision=bool(info.get("physical_collision", False)),
                        custom_obstacles_physical=bool(info.get("custom_obstacles_physical", False)),
                        obstacle_body_ids=dict(info.get("obstacle_body_ids", {})),
                        platform_terminated=bool(info.get("platform_terminated", False)),
                        platform_truncated=bool(info.get("platform_truncated", False)),
                        onboard_camera=dict(info.get("onboard_camera", {"enabled": False})),
                    )
                )
                last_info = info
                if terminated or truncated:
                    break
                if realtime or gui:
                    time.sleep(float(scenario.dt))
            summary = RolloutSummary(
                task_id="TASK_05",
                output_type="diagnostic",
                platform_id=last_info["platform_id"],
                scenario_id=scenario.scenario_id,
                seed=scenario.seed,
                policy_id=policy_id,
                steps=int(last_info.get("step", 0)),
                final_distance_to_goal=float(last_info["distance_to_goal"]),
                min_clearance=float(min_clearance),
                collision=bool(last_info["collision"]),
                success=bool(last_info["success"]),
                timeout=bool(last_info["timeout"]),
            )
            writer.write_summary(summary)
        if gui:
            _hold_gui(env, hold_seconds)
    finally:
        env.close()
    print(json.dumps({"output_path": str(output), **summary.__dict__}, indent=2, sort_keys=True))
    return output


def _hold_gui(env: Task04GymPybulletDronesRLEnv, hold_seconds: float | None) -> None:
    try:
        import pybullet as p
    except ImportError:
        return
    client = None
    if env.adapter is not None:
        client = env.adapter.pybullet_client
    if client is None:
        return
    if hold_seconds is not None:
        deadline = time.monotonic() + max(0.0, float(hold_seconds))
        while p.isConnected(client) and time.monotonic() < deadline:
            p.stepSimulation(physicsClientId=client)
            time.sleep(1.0 / 30.0)
        return
    print("[info] TASK_05 GUI is being held open. Close the PyBullet window or press Ctrl+C to exit.")
    try:
        while p.isConnected(client):
            p.stepSimulation(physicsClientId=client)
            time.sleep(1.0 / 30.0)
    except KeyboardInterrupt:
        pass
