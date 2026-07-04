"""Gymnasium wrapper for TASK_04 RL-ready diagnostics."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from pirl_navrl.evaluation.reward import Task04RewardConfig, compute_task04_reward
from pirl_navrl.platforms.gym_pybullet_drones.observation_adapter import (
    flatten_observation,
    observation_space_for_scenario,
)
from pirl_navrl.platforms.gym_pybullet_drones.simple_adapter import GymPybulletDronesSimpleAdapter
from pirl_navrl.scenarios.core import ScenarioConfig, make_scenario


class Task04GymPybulletDronesRLEnv(gym.Env):
    metadata = {"render_modes": ["human"], "render_fps": 30}

    def __init__(
        self,
        *,
        scenario: ScenarioConfig | None = None,
        scenario_id: str = "task03_static_nav_v0",
        seed: int = 0,
        max_speed: float = 1.0,
        gui: bool = False,
        camera_mode: str = "manual",
        camera_control: str = "orbit",
        enable_mouse_picking: bool = False,
        show_pybullet_ui: bool = False,
        show_camera_preview: bool = False,
        show_drone_marker: bool = False,
        enable_onboard_camera: bool = False,
        onboard_camera_width: int = 640,
        onboard_camera_height: int = 480,
        onboard_camera_period: int = 4,
        clean_visuals: bool = False,
        reward_config: Task04RewardConfig | None = None,
    ) -> None:
        super().__init__()
        self.scenario = scenario or make_scenario(scenario_id, seed=seed)
        self.max_speed = max_speed
        self.gui = gui
        self.camera_mode = camera_mode
        self.camera_control = camera_control
        self.enable_mouse_picking = enable_mouse_picking
        self.show_pybullet_ui = show_pybullet_ui
        self.show_camera_preview = show_camera_preview
        self.show_drone_marker = show_drone_marker
        self.enable_onboard_camera = enable_onboard_camera
        self.onboard_camera_width = onboard_camera_width
        self.onboard_camera_height = onboard_camera_height
        self.onboard_camera_period = onboard_camera_period
        self.clean_visuals = clean_visuals
        self.reward_config = reward_config or Task04RewardConfig()
        self.adapter: GymPybulletDronesSimpleAdapter | None = None
        self.previous_obs_dict: dict[str, Any] | None = None
        self.observation_space = observation_space_for_scenario(self.scenario)
        self.action_space = spaces.Box(
            low=np.full((3,), -1.0, dtype=np.float32),
            high=np.full((3,), 1.0, dtype=np.float32),
            dtype=np.float32,
        )

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self.scenario = replace(self.scenario, seed=int(seed))
            self.observation_space = observation_space_for_scenario(self.scenario)
        del options
        self.close()
        self.adapter = GymPybulletDronesSimpleAdapter(
            max_speed=self.max_speed,
            gui=self.gui,
            camera_mode=self.camera_mode,
            camera_control=self.camera_control,
            enable_mouse_picking=self.enable_mouse_picking,
            show_pybullet_ui=self.show_pybullet_ui,
            show_camera_preview=self.show_camera_preview,
            show_drone_marker=self.show_drone_marker,
            enable_onboard_camera=self.enable_onboard_camera,
            onboard_camera_width=self.onboard_camera_width,
            onboard_camera_height=self.onboard_camera_height,
            onboard_camera_period=self.onboard_camera_period,
            clean_visuals=self.clean_visuals,
        )
        obs_dict = self.adapter.reset(self.scenario)
        self.previous_obs_dict = obs_dict
        observation = flatten_observation(obs_dict)
        info = self._info_from_obs(obs_dict, collision=False, success=False, timeout=False)
        info["reward_terms"] = {}
        return observation, info

    def step(self, action):
        if self.adapter is None or self.previous_obs_dict is None:
            raise RuntimeError("reset() must be called before step()")
        normalized_action = np.clip(np.asarray(action, dtype=np.float32).reshape(3), -1.0, 1.0)
        desired_velocity = normalized_action * float(self.max_speed)
        obs_dict, _platform_reward, terminated, truncated, info = self.adapter.step(desired_velocity)
        event_flags = {
            "collision": bool(info["collision"]),
            "success": bool(info["success"]),
            "timeout": bool(info["timeout"]),
        }
        reward, reward_terms = compute_task04_reward(
            self.previous_obs_dict,
            obs_dict,
            normalized_action,
            event_flags,
            self.reward_config,
        )
        self.previous_obs_dict = obs_dict
        observation = flatten_observation(obs_dict)
        info = {
            **info,
            "reward_terms": reward_terms,
        }
        return observation, float(reward), bool(terminated), bool(truncated), info

    def render(self):
        if self.adapter is not None and self.adapter.env is not None:
            return self.adapter.env.render()
        return None

    def close(self) -> None:
        if self.adapter is not None:
            self.adapter.close()
            self.adapter = None

    def _info_from_obs(
        self,
        obs_dict: dict[str, Any],
        *,
        collision: bool,
        success: bool,
        timeout: bool,
    ) -> dict[str, Any]:
        return {
            "platform_id": GymPybulletDronesSimpleAdapter.platform_id,
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "position": tuple(float(v) for v in obs_dict["position"]),
            "velocity": tuple(float(v) for v in obs_dict["velocity"]),
            "distance_to_goal": float(obs_dict["distance_to_goal"]),
            "min_clearance": float(obs_dict["min_clearance"]),
            "collision": collision,
            "success": success,
            "timeout": timeout,
        }
