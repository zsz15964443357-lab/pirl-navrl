"""TASK_03 diagnostic kinematic environment.

This environment is only a diagnostic fallback for rollout plumbing. It is not
the final paper environment and must not be reported as a baseline simulator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from pirl_navrl.scenarios.core import ObstacleConfig, ScenarioConfig, Vector3


def vector_norm(vector: Vector3) -> float:
    return math.sqrt(sum(component * component for component in vector))


def distance(left: Vector3, right: Vector3) -> float:
    return vector_norm((left[0] - right[0], left[1] - right[1], left[2] - right[2]))


def clip_velocity(action: Any, max_speed: float) -> Vector3:
    values = tuple(float(value) for value in action)
    if len(values) != 3:
        raise ValueError("diagnostic kinematic env expects a 3D velocity action")
    norm = vector_norm(values)  # type: ignore[arg-type]
    if norm <= max_speed or norm == 0.0:
        return values  # type: ignore[return-value]
    scale = max_speed / norm
    return (values[0] * scale, values[1] * scale, values[2] * scale)


def obstacle_clearance(position: Vector3, obstacle: ObstacleConfig, elapsed: float) -> float:
    center = obstacle.position_at(elapsed)
    if obstacle.kind == "cylinder":
        horizontal = math.hypot(position[0] - center[0], position[1] - center[1])
        return horizontal - obstacle.radius
    return distance(position, center) - obstacle.radius


@dataclass
class DiagnosticKinematicState:
    position: Vector3
    velocity: Vector3
    step_count: int
    elapsed: float
    collision: bool = False
    success: bool = False
    timeout: bool = False


class DiagnosticKinematicEnv:
    platform_id = "diagnostic_kinematic_env"

    def __init__(self, *, max_speed: float = 1.0) -> None:
        self.max_speed = max_speed
        self.scenario: ScenarioConfig | None = None
        self.state: DiagnosticKinematicState | None = None

    def reset(self, scenario: ScenarioConfig) -> dict[str, Any]:
        self.scenario = scenario
        self.state = DiagnosticKinematicState(
            position=scenario.start,
            velocity=(0.0, 0.0, 0.0),
            step_count=0,
            elapsed=0.0,
        )
        return self.get_observation()

    def step(self, action: Any) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        scenario = self._scenario()
        state = self._state()
        velocity = clip_velocity(action, self.max_speed)
        raw_next = (
            state.position[0] + velocity[0] * scenario.dt,
            state.position[1] + velocity[1] * scenario.dt,
            state.position[2] + velocity[2] * scenario.dt,
        )
        next_position = scenario.bounds.clamp(raw_next)
        next_elapsed = state.elapsed + scenario.dt
        step_count = state.step_count + 1
        min_clearance = self.min_clearance(next_position, next_elapsed)
        collision = min_clearance <= scenario.collision_radius
        success = distance(next_position, scenario.goal) <= scenario.success_radius
        timeout = step_count >= scenario.max_steps and not success and not collision
        self.state = DiagnosticKinematicState(
            position=next_position,
            velocity=velocity,
            step_count=step_count,
            elapsed=next_elapsed,
            collision=collision,
            success=success,
            timeout=timeout,
        )
        terminated = collision or success
        truncated = timeout
        info = self._info(action=velocity, min_clearance=min_clearance)
        return self.get_observation(), 0.0, terminated, truncated, info

    def get_observation(self) -> dict[str, Any]:
        scenario = self._scenario()
        state = self._state()
        return {
            "position": state.position,
            "velocity": state.velocity,
            "goal": scenario.goal,
            "step": state.step_count,
            "elapsed": state.elapsed,
            "bounds": scenario.bounds,
            "static_obstacles": scenario.static_obstacles,
            "dynamic_obstacles": scenario.dynamic_obstacles,
        }

    def min_clearance(self, position: Vector3 | None = None, elapsed: float | None = None) -> float:
        scenario = self._scenario()
        state = self._state()
        query_position = state.position if position is None else position
        query_elapsed = state.elapsed if elapsed is None else elapsed
        clearances = [
            obstacle_clearance(query_position, obstacle, query_elapsed)
            for obstacle in scenario.all_obstacles()
        ]
        return min(clearances) if clearances else math.inf

    def _info(self, *, action: Vector3, min_clearance: float) -> dict[str, Any]:
        scenario = self._scenario()
        state = self._state()
        return {
            "platform_id": self.platform_id,
            "step": state.step_count,
            "position": state.position,
            "velocity": state.velocity,
            "goal": scenario.goal,
            "action": action,
            "distance_to_goal": distance(state.position, scenario.goal),
            "min_clearance": min_clearance,
            "collision": state.collision,
            "success": state.success,
            "timeout": state.timeout,
        }

    def _scenario(self) -> ScenarioConfig:
        if self.scenario is None:
            raise RuntimeError("reset(scenario) must be called before using the environment")
        return self.scenario

    def _state(self) -> DiagnosticKinematicState:
        if self.state is None:
            raise RuntimeError("reset(scenario) must be called before using the environment")
        return self.state
