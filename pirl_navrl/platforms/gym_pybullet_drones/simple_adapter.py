"""Explicit skeleton for the future gym-pybullet-drones TASK_04 adapter."""

from __future__ import annotations

from pirl_navrl.scenarios.core import ScenarioConfig


class GymPybulletDronesSimpleAdapter:
    platform_id = "gym_pybullet_drones_adapter_skeleton"

    def __init__(self) -> None:
        try:
            import gym_pybullet_drones  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "gym-pybullet-drones is not available. Install the external "
                "dependency before using this adapter; no diagnostic fallback "
                "is provided here."
            ) from exc

        raise NotImplementedError(
            "TASK_03 only defines the gym-pybullet-drones adapter boundary. "
            "The real control loop is reserved for a later task."
        )

    def reset(self, scenario: ScenarioConfig) -> None:
        del scenario
        raise NotImplementedError

    def step(self, action):
        del action
        raise NotImplementedError
