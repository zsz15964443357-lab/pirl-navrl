"""Reward profile presets for TASK_06 diagnostic PPO training."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pirl_navrl.evaluation.reward import Task04RewardConfig, compute_task04_reward

@dataclass(frozen=True)
class Task06RewardProfile:
    name: str
    base: Task04RewardConfig
    dynamic_risk_weight: float = 0.0
    latent_clearance_weight: float = 0.0
    goal_alignment_weight: float = 0.0
    vertical_action_weight: float = 0.0
    altitude_error_weight: float = 0.0
    proximity_action_weight: float = 0.0
    proximity_action_threshold: float = 0.8
    near_goal_weight: float = 0.0
    near_goal_threshold: float = 1.0
    smoothness_weight: float = 0.0


def _static_profile(
    *,
    name: str,
    progress_weight: float,
    distance_weight: float,
    action_weight: float,
    clearance_weight: float,
    clearance_margin: float,
    collision_penalty: float,
    success_bonus: float,
    timeout_penalty: float,
    goal_alignment_weight: float,
    near_goal_weight: float,
    near_goal_threshold: float,
    smoothness_weight: float,
) -> Task06RewardProfile:
    return Task06RewardProfile(
        name=name,
        base=Task04RewardConfig(
            progress_weight=progress_weight,
            distance_weight=distance_weight,
            action_weight=action_weight,
            clearance_weight=clearance_weight,
            clearance_margin=clearance_margin,
            collision_penalty=collision_penalty,
            success_bonus=success_bonus,
            timeout_penalty=timeout_penalty,
        ),
        goal_alignment_weight=goal_alignment_weight,
        vertical_action_weight=0.05,
        near_goal_weight=near_goal_weight,
        near_goal_threshold=near_goal_threshold,
        smoothness_weight=smoothness_weight,
    )


STATIC_AVOIDANCE_BALANCED = _static_profile(
    name="static_avoidance_balanced",
    progress_weight=2.0,
    distance_weight=0.07,
    action_weight=0.028,
    clearance_weight=1.75,
    clearance_margin=1.45,
    collision_penalty=180.0,
    success_bonus=45.0,
    timeout_penalty=8.0,
    goal_alignment_weight=0.24,
    near_goal_weight=0.12,
    near_goal_threshold=1.2,
    smoothness_weight=0.09,
)


PROFILES: dict[str, Task06RewardProfile] = {
    "goal_only": Task06RewardProfile(
        name="goal_only",
        base=Task04RewardConfig(clearance_weight=0.0, collision_penalty=8.0, success_bonus=12.0),
    ),
    "static_avoidance": STATIC_AVOIDANCE_BALANCED,
    "static_avoidance_aggressive": _static_profile(
        name="static_avoidance_aggressive",
        progress_weight=2.2,
        distance_weight=0.08,
        action_weight=0.006,
        clearance_weight=1.25,
        clearance_margin=1.35,
        collision_penalty=140.0,
        success_bonus=35.0,
        timeout_penalty=5.0,
        goal_alignment_weight=0.28,
        near_goal_weight=0.08,
        near_goal_threshold=1.0,
        smoothness_weight=0.08,
    ),
    "static_avoidance_aggressive_altitude": Task06RewardProfile(
        name="static_avoidance_aggressive_altitude",
        base=Task04RewardConfig(
            progress_weight=2.2,
            distance_weight=0.08,
            action_weight=0.006,
            clearance_weight=1.3,
            clearance_margin=1.35,
            collision_penalty=155.0,
            success_bonus=38.0,
            timeout_penalty=5.0,
        ),
        goal_alignment_weight=0.28,
        vertical_action_weight=0.05,
        altitude_error_weight=0.2,
        near_goal_weight=0.08,
        near_goal_threshold=1.0,
        smoothness_weight=0.08,
    ),
    "static_avoidance_navrl_speed_safety": Task06RewardProfile(
        name="static_avoidance_navrl_speed_safety",
        base=Task04RewardConfig(
            progress_weight=2.2,
            distance_weight=0.08,
            action_weight=0.006,
            clearance_weight=1.35,
            clearance_margin=1.35,
            collision_penalty=170.0,
            success_bonus=38.0,
            timeout_penalty=5.0,
        ),
        goal_alignment_weight=0.28,
        vertical_action_weight=0.05,
        altitude_error_weight=0.12,
        proximity_action_weight=0.42,
        proximity_action_threshold=0.85,
        near_goal_weight=0.08,
        near_goal_threshold=1.0,
        smoothness_weight=0.08,
    ),
    "static_avoidance_aggressive_safe": _static_profile(
        name="static_avoidance_aggressive_safe",
        progress_weight=2.1,
        distance_weight=0.08,
        action_weight=0.012,
        clearance_weight=1.55,
        clearance_margin=1.45,
        collision_penalty=220.0,
        success_bonus=45.0,
        timeout_penalty=6.0,
        goal_alignment_weight=0.26,
        near_goal_weight=0.1,
        near_goal_threshold=1.0,
        smoothness_weight=0.08,
    ),
    "static_avoidance_cautious": _static_profile(
        name="static_avoidance_cautious",
        progress_weight=1.7,
        distance_weight=0.06,
        action_weight=0.055,
        clearance_weight=2.2,
        clearance_margin=1.55,
        collision_penalty=220.0,
        success_bonus=35.0,
        timeout_penalty=5.0,
        goal_alignment_weight=0.18,
        near_goal_weight=0.08,
        near_goal_threshold=1.0,
        smoothness_weight=0.12,
    ),
    "static_avoidance_balanced": STATIC_AVOIDANCE_BALANCED,
    "dynamic_avoidance": Task06RewardProfile(
        name="dynamic_avoidance",
        base=Task04RewardConfig(
            progress_weight=1.6,
            distance_weight=0.05,
            action_weight=0.005,
            clearance_weight=1.05,
            clearance_margin=1.35,
            collision_penalty=100.0,
            success_bonus=24.0,
            timeout_penalty=4.0,
        ),
        dynamic_risk_weight=0.75,
        goal_alignment_weight=0.22,
        vertical_action_weight=0.04,
    ),
    "dynamic_avoidance_reach": Task06RewardProfile(
        name="dynamic_avoidance_reach",
        base=Task04RewardConfig(
            progress_weight=2.15,
            distance_weight=0.08,
            action_weight=0.008,
            clearance_weight=1.35,
            clearance_margin=1.35,
            collision_penalty=165.0,
            success_bonus=42.0,
            timeout_penalty=6.0,
        ),
        dynamic_risk_weight=0.8,
        goal_alignment_weight=0.27,
        vertical_action_weight=0.05,
        altitude_error_weight=0.18,
        near_goal_weight=0.08,
        near_goal_threshold=1.0,
        smoothness_weight=0.06,
    ),
    "latent_risk": Task06RewardProfile(
        name="latent_risk",
        base=Task04RewardConfig(
            progress_weight=1.5,
            distance_weight=0.05,
            action_weight=0.005,
            clearance_weight=1.1,
            clearance_margin=1.4,
            collision_penalty=100.0,
            success_bonus=24.0,
            timeout_penalty=4.0,
        ),
        dynamic_risk_weight=0.7,
        latent_clearance_weight=0.45,
        goal_alignment_weight=0.2,
        vertical_action_weight=0.04,
    ),
    "latent_risk_reach": Task06RewardProfile(
        name="latent_risk_reach",
        base=Task04RewardConfig(
            progress_weight=2.1,
            distance_weight=0.08,
            action_weight=0.009,
            clearance_weight=1.45,
            clearance_margin=1.4,
            collision_penalty=175.0,
            success_bonus=42.0,
            timeout_penalty=6.0,
        ),
        dynamic_risk_weight=0.85,
        latent_clearance_weight=0.35,
        goal_alignment_weight=0.25,
        vertical_action_weight=0.05,
        altitude_error_weight=0.18,
        near_goal_weight=0.08,
        near_goal_threshold=1.0,
        smoothness_weight=0.07,
    ),
}


def get_reward_profile(name: str) -> Task06RewardProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        options = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown TASK_06 reward profile {name!r}; options: {options}") from exc


def compute_task06_reward(
    previous_obs: dict[str, Any],
    current_obs: dict[str, Any],
    action,
    event_flags: dict[str, bool],
    *,
    profile_name: str,
    dynamic_relative_velocity=None,
    previous_action=None,
) -> tuple[float, dict[str, float]]:
    profile = get_reward_profile(profile_name)
    reward, terms = compute_task04_reward(previous_obs, current_obs, action, event_flags, profile.base)
    action_array = np.asarray(action, dtype=np.float32).reshape(-1)
    relative_goal = np.asarray(previous_obs["relative_goal"], dtype=np.float32).reshape(3)
    goal_norm = float(np.linalg.norm(relative_goal))
    action_norm = float(np.linalg.norm(action_array[:3]))
    goal_alignment = 0.0
    if goal_norm > 1e-6 and action_norm > 1e-6 and profile.goal_alignment_weight > 0.0:
        goal_direction = relative_goal / goal_norm
        action_direction = action_array[:3] / action_norm
        goal_alignment = profile.goal_alignment_weight * float(np.dot(action_direction, goal_direction))
    vertical_action = 0.0
    if profile.vertical_action_weight > 0.0 and action_array.size >= 3:
        vertical_action = -profile.vertical_action_weight * abs(float(action_array[2]))
    altitude_error = 0.0
    if profile.altitude_error_weight > 0.0:
        altitude_error = -profile.altitude_error_weight * abs(float(current_obs["relative_goal"][2]))
    proximity_action = 0.0
    if profile.proximity_action_weight > 0.0:
        clearance_deficit = max(
            0.0,
            profile.proximity_action_threshold - float(current_obs["min_clearance"]),
        )
        proximity_action = -profile.proximity_action_weight * clearance_deficit * action_norm
    near_goal = 0.0
    if profile.near_goal_weight > 0.0:
        distance = float(current_obs["distance_to_goal"])
        near_goal = profile.near_goal_weight * max(0.0, profile.near_goal_threshold - distance)
    smoothness = 0.0
    if previous_action is not None and profile.smoothness_weight > 0.0:
        previous_action_array = np.asarray(previous_action, dtype=np.float32).reshape(-1)
        smoothness = -profile.smoothness_weight * float(
            np.linalg.norm(action_array[:3] - previous_action_array[:3])
        )
    dynamic_risk = 0.0
    if dynamic_relative_velocity is not None and profile.dynamic_risk_weight > 0.0:
        rel_speed = float(np.linalg.norm(np.asarray(dynamic_relative_velocity, dtype=np.float32).reshape(-1)))
        clearance = float(current_obs["min_clearance"])
        dynamic_risk = -profile.dynamic_risk_weight * rel_speed * max(0.0, 1.0 - clearance)
    latent_clearance = 0.0
    if profile.latent_clearance_weight > 0.0:
        latent_clearance = -profile.latent_clearance_weight * max(0.0, 1.2 - float(current_obs["min_clearance"]))
    terms["dynamic_risk_penalty"] = float(dynamic_risk)
    terms["latent_clearance_penalty"] = float(latent_clearance)
    terms["goal_alignment_reward"] = float(goal_alignment)
    terms["vertical_action_penalty"] = float(vertical_action)
    terms["altitude_error_penalty"] = float(altitude_error)
    terms["proximity_action_penalty"] = float(proximity_action)
    terms["near_goal_reward"] = float(near_goal)
    terms["smoothness_penalty"] = float(smoothness)
    total = float(
        reward
        + dynamic_risk
        + latent_clearance
        + goal_alignment
        + vertical_action
        + altitude_error
        + proximity_action
        + near_goal
        + smoothness
    )
    if not np.isfinite(total):
        raise ValueError("TASK_06 reward must be finite")
    return total, terms
