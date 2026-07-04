"""Small diagnostic policies used to exercise the TASK_03 rollout stack."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping

from pirl_navrl.scenarios.core import ScenarioConfig, Vector3


def _norm(vector: Vector3) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _clip_norm(vector: Vector3, max_norm: float) -> Vector3:
    norm = _norm(vector)
    if norm <= max_norm or norm == 0.0:
        return vector
    scale = max_norm / norm
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


class RandomVelocityPolicy:
    """Seeded random velocity policy for diagnostic plumbing checks."""

    policy_id = "random_velocity_debug"

    def __init__(self, *, max_speed: float = 0.8, seed: int = 0) -> None:
        self.max_speed = max_speed
        self.seed = seed
        self._rng = random.Random(seed)

    def reset(self, scenario: ScenarioConfig) -> None:
        self._rng = random.Random(self.seed + scenario.seed)

    def act(self, observation: Mapping[str, Any]) -> Vector3:
        del observation
        vector = (
            self._rng.uniform(-1.0, 1.0),
            self._rng.uniform(-1.0, 1.0),
            self._rng.uniform(-0.25, 0.25),
        )
        return _clip_norm(vector, self.max_speed)


class GoalSeekingVelocityPolicy:
    """Direct-to-goal diagnostic velocity policy without obstacle reasoning."""

    policy_id = "goal_seeking_velocity_debug"

    def __init__(self, *, max_speed: float = 1.0) -> None:
        self.max_speed = max_speed
        self.scenario: ScenarioConfig | None = None

    def reset(self, scenario: ScenarioConfig) -> None:
        self.scenario = scenario

    def act(self, observation: Mapping[str, Any]) -> Vector3:
        position = tuple(float(value) for value in observation["position"])
        goal = tuple(float(value) for value in observation["goal"])
        direction = (
            goal[0] - position[0],
            goal[1] - position[1],
            goal[2] - position[2],
        )
        return _clip_norm(direction, self.max_speed)
