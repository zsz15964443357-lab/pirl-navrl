"""TASK_04 gym-pybullet-drones velocity adapter."""

from __future__ import annotations

from typing import Any

import numpy as np
import pybullet as p

from pirl_navrl.platforms.gym_pybullet_drones.action_adapter import adapt_desired_velocity
from pirl_navrl.platforms.gym_pybullet_drones.observation_adapter import build_observation_dict
from pirl_navrl.scenarios.core import ObstacleConfig, ScenarioConfig


class GymPybulletDronesSimpleAdapter:
    platform_id = "gym_pybullet_drones_velocity_adapter_debug"

    def __init__(
        self,
        *,
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
        near_goal_speed_radius: float = 0.0,
        near_goal_min_speed_scale: float = 0.18,
        altitude_hold: bool = True,
        altitude_hold_gain: float = 1.2,
        altitude_hold_max_speed: float = 0.55,
        pyb_freq: int = 240,
        ctrl_freq: int = 48,
    ) -> None:
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
        self.onboard_camera_period = max(1, onboard_camera_period)
        self.clean_visuals = clean_visuals
        self.near_goal_speed_radius = float(near_goal_speed_radius)
        self.near_goal_min_speed_scale = float(near_goal_min_speed_scale)
        self.altitude_hold = bool(altitude_hold)
        self.altitude_hold_gain = float(altitude_hold_gain)
        self.altitude_hold_max_speed = float(altitude_hold_max_speed)
        self.pyb_freq = pyb_freq
        self.ctrl_freq = ctrl_freq
        self.env = None
        self.scenario: ScenarioConfig | None = None
        self.step_count = 0
        self.elapsed = 0.0
        self.last_platform_observation = None
        self.last_observation: dict[str, Any] | None = None
        self.pybullet_client: int | None = None
        self.drone_body_id: int | None = None
        self.obstacle_body_ids: dict[str, int] = {}
        self.marker_body_ids: dict[str, int] = {}
        self.drone_marker_body_id: int | None = None
        self.last_marker_position: tuple[float, float, float] | None = None
        self.last_onboard_camera: dict[str, Any] | None = None
        self._active_mouse_buttons: set[int] = set()
        self._last_mouse_xy: tuple[float, float] | None = None
        try:
            from gym_pybullet_drones.envs.VelocityAviary import VelocityAviary
            from gym_pybullet_drones.utils.enums import DroneModel, Physics
        except ImportError as exc:
            raise RuntimeError(
                "gym-pybullet-drones is not available. Install the external "
                "dependency before using this adapter; no diagnostic fallback "
                "is provided here."
            ) from exc
        self._velocity_aviary_cls = VelocityAviary
        self._drone_model = DroneModel
        self._physics = Physics

    def reset(self, scenario: ScenarioConfig) -> dict[str, Any]:
        self.close()
        self.scenario = scenario
        self.step_count = 0
        self.elapsed = 0.0
        self.env = self._velocity_aviary_cls(
            drone_model=self._drone_model.CF2X,
            num_drones=1,
            initial_xyzs=np.asarray([scenario.start], dtype=np.float32),
            physics=self._physics.PYB,
            pyb_freq=self.pyb_freq,
            ctrl_freq=self.ctrl_freq,
            gui=self.gui,
            record=False,
            obstacles=False,
            user_debug_gui=False,
            output_folder="/tmp/pirl_navrl_task04",
        )
        platform_obs, _info = self.env.reset(seed=scenario.seed)
        self.pybullet_client = int(self.env.getPyBulletClient())
        self.drone_body_id = int(self.env.getDroneIds()[0])
        self._configure_live_gui()
        self._configure_scene_visual_quality()
        self._create_obstacle_bodies()
        self._create_scene_markers()
        self._set_initial_debug_camera()
        self.last_platform_observation = platform_obs
        self.last_observation = build_observation_dict(
            platform_observation=platform_obs,
            scenario=scenario,
            step_count=self.step_count,
            elapsed=self.elapsed,
        )
        return self.last_observation

    def step(self, desired_velocity) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        if self.env is None or self.scenario is None:
            raise RuntimeError("reset(scenario) must be called before step()")
        desired_velocity, near_goal_speed_scale = self._scale_velocity_near_goal(desired_velocity)
        desired_velocity = self._apply_altitude_hold(desired_velocity)
        action_result = adapt_desired_velocity(
            desired_velocity,
            "normalized_velocity",
            max_speed=self.max_speed,
        )
        env_action = np.asarray([action_result.velocity_aviary_action], dtype=np.float32)
        platform_obs, platform_reward, platform_terminated, platform_truncated, platform_info = self.env.step(env_action)
        self.step_count += 1
        self.elapsed += 1.0 / float(self.ctrl_freq)
        observation = build_observation_dict(
            platform_observation=platform_obs,
            scenario=self.scenario,
            step_count=self.step_count,
            elapsed=self.elapsed,
        )
        self.last_platform_observation = platform_obs
        self.last_observation = observation
        position = tuple(float(v) for v in observation["position"])
        self._handle_orbit_mouse_camera()
        self._update_live_camera(position)
        self._update_drone_marker(position)
        self._update_obstacle_bodies()
        onboard_camera = self._maybe_sample_onboard_camera(position)
        safety_collision = bool(observation["min_clearance"] <= self.scenario.collision_radius)
        physical_collision = self._physical_obstacle_contact()
        collision = bool(safety_collision or physical_collision)
        reached_goal = bool(observation["distance_to_goal"] <= self.scenario.success_radius)
        success = bool(reached_goal and not collision)
        timeout = bool(self.step_count >= self.scenario.max_steps and not collision and not success)
        terminated = bool(success or collision)
        truncated = bool(timeout)
        info = {
            "platform_id": self.platform_id,
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "step": self.step_count,
            "position": tuple(float(v) for v in observation["position"]),
            "velocity": tuple(float(v) for v in observation["velocity"]),
            "goal": self.scenario.goal,
            "distance_to_goal": float(observation["distance_to_goal"]),
            "min_clearance": float(observation["min_clearance"]),
            "collision": collision,
            "safety_collision": safety_collision,
            "physical_collision": physical_collision,
            "reached_goal": reached_goal,
            "success": success,
            "timeout": timeout,
            "custom_obstacles_physical": True,
            "obstacle_body_ids": dict(self.obstacle_body_ids),
            "near_goal_speed_scale": near_goal_speed_scale,
            "altitude_hold": self.altitude_hold,
            "raw_desired_velocity": action_result.raw_desired_velocity,
            "clipped_desired_velocity": action_result.clipped_desired_velocity,
            "applied_action": action_result.applied_action,
            "velocity_aviary_action": action_result.velocity_aviary_action,
            "platform_reward": float(platform_reward),
            "platform_terminated": bool(platform_terminated),
            "platform_truncated": bool(platform_truncated),
            "onboard_camera": onboard_camera,
            "platform_info": platform_info,
        }
        return observation, float(platform_reward), terminated, truncated, info

    def _scale_velocity_near_goal(self, desired_velocity) -> tuple[np.ndarray, float]:
        velocity = np.asarray(desired_velocity, dtype=np.float32).reshape(3)
        if self.last_observation is None or self.near_goal_speed_radius <= 0.0:
            return velocity, 1.0
        distance = float(self.last_observation["distance_to_goal"])
        if distance >= self.near_goal_speed_radius:
            return velocity, 1.0
        scale = float(
            np.clip(
                distance / max(self.near_goal_speed_radius, 1e-6),
                self.near_goal_min_speed_scale,
                1.0,
            )
        )
        return (velocity * scale).astype(np.float32), scale

    def _apply_altitude_hold(self, desired_velocity: np.ndarray) -> np.ndarray:
        velocity = np.asarray(desired_velocity, dtype=np.float32).reshape(3).copy()
        if not self.altitude_hold or self.last_observation is None:
            return velocity
        z_error = float(self.last_observation["relative_goal"][2])
        max_vertical = max(0.0, self.altitude_hold_max_speed)
        velocity[2] = float(np.clip(self.altitude_hold_gain * z_error, -max_vertical, max_vertical))
        return velocity.astype(np.float32)

    def get_observation(self) -> dict[str, Any]:
        if self.last_observation is None:
            raise RuntimeError("reset(scenario) must be called before get_observation()")
        return self.last_observation

    def close(self) -> None:
        if self.env is None:
            return
        self.env.close()
        self.env = None
        self.pybullet_client = None
        self.drone_body_id = None
        self.obstacle_body_ids = {}
        self.marker_body_ids = {}
        self.drone_marker_body_id = None
        self.last_marker_position = None
        self.last_onboard_camera = None
        self._active_mouse_buttons = set()
        self._last_mouse_xy = None

    def _create_obstacle_bodies(self) -> None:
        if self.scenario is None or self.pybullet_client is None:
            return
        self.obstacle_body_ids = {}
        for obstacle in self.scenario.all_obstacles():
            body_id = self._create_obstacle_body(obstacle, elapsed=0.0)
            self.obstacle_body_ids[obstacle.obstacle_id] = body_id

    def _create_scene_markers(self) -> None:
        if self.scenario is None or self.pybullet_client is None:
            return
        self.marker_body_ids = {
            "start": self._create_marker(self.scenario.start, radius=0.18, color=[0.05, 0.25, 0.95, 0.9]),
            "goal": self._create_marker(self.scenario.goal, radius=0.26, color=[0.0, 0.75, 0.22, 0.95]),
        }

    def _configure_live_gui(self) -> None:
        if not self.gui or self.pybullet_client is None:
            return
        if self.camera_mode not in {"fixed", "follow", "manual"}:
            raise ValueError("camera_mode must be one of: fixed, follow, manual")
        if self.camera_control not in {"orbit", "pybullet"}:
            raise ValueError("camera_control must be one of: orbit, pybullet")
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, int(self.show_pybullet_ui), physicsClientId=self.pybullet_client)
        mouse_picking = bool(self.enable_mouse_picking and self.camera_control == "pybullet")
        p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, int(mouse_picking), physicsClientId=self.pybullet_client)
        p.configureDebugVisualizer(p.COV_ENABLE_KEYBOARD_SHORTCUTS, 1, physicsClientId=self.pybullet_client)
        p.configureDebugVisualizer(
            p.COV_ENABLE_RGB_BUFFER_PREVIEW,
            int(self.show_camera_preview),
            physicsClientId=self.pybullet_client,
        )
        p.configureDebugVisualizer(
            p.COV_ENABLE_DEPTH_BUFFER_PREVIEW,
            int(self.show_camera_preview),
            physicsClientId=self.pybullet_client,
        )
        p.configureDebugVisualizer(
            p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW,
            int(self.show_camera_preview),
            physicsClientId=self.pybullet_client,
        )
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, physicsClientId=self.pybullet_client)

    def _handle_orbit_mouse_camera(self) -> None:
        if (
            not self.gui
            or self.pybullet_client is None
            or self.camera_mode != "manual"
            or self.camera_control != "orbit"
        ):
            return
        try:
            events = p.getMouseEvents(physicsClientId=self.pybullet_client)
        except Exception:
            return
        if not events:
            return
        for event in events:
            if len(event) < 5:
                continue
            x = float(event[1])
            y = float(event[2])
            button = int(event[3])
            state = int(event[4])
            if button >= 0 and state & p.KEY_WAS_RELEASED:
                self._active_mouse_buttons.discard(button)
                if not self._active_mouse_buttons:
                    self._last_mouse_xy = None
                continue
            if button >= 0 and (state & p.KEY_WAS_TRIGGERED or state & p.KEY_IS_DOWN):
                if button in {3, 4}:
                    self._zoom_orbit_camera(0.88 if button == 3 else 1.14)
                    continue
                self._active_mouse_buttons.add(button)
                if self._last_mouse_xy is None:
                    self._last_mouse_xy = (x, y)
                    continue
            if not self._active_mouse_buttons:
                self._last_mouse_xy = (x, y)
                continue
            if self._last_mouse_xy is None:
                self._last_mouse_xy = (x, y)
                continue
            dx = x - self._last_mouse_xy[0]
            dy = y - self._last_mouse_xy[1]
            self._last_mouse_xy = (x, y)
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                continue
            if 1 in self._active_mouse_buttons:
                self._zoom_orbit_camera(1.0 + float(np.clip(dy * 0.01, -0.5, 0.5)))
            else:
                self._rotate_orbit_camera(dx=dx, dy=dy)

    def _rotate_orbit_camera(self, *, dx: float, dy: float) -> None:
        if self.pybullet_client is None:
            return
        camera = p.getDebugVisualizerCamera(physicsClientId=self.pybullet_client)
        p.resetDebugVisualizerCamera(
            cameraDistance=float(camera[10]),
            cameraYaw=float(camera[8]) + dx * 0.25,
            cameraPitch=float(np.clip(float(camera[9]) + dy * 0.25, -89.0, 89.0)),
            cameraTargetPosition=list(camera[11]),
            physicsClientId=self.pybullet_client,
        )

    def _zoom_orbit_camera(self, factor: float) -> None:
        if self.pybullet_client is None:
            return
        camera = p.getDebugVisualizerCamera(physicsClientId=self.pybullet_client)
        p.resetDebugVisualizerCamera(
            cameraDistance=float(np.clip(float(camera[10]) * factor, 0.6, 30.0)),
            cameraYaw=float(camera[8]),
            cameraPitch=float(camera[9]),
            cameraTargetPosition=list(camera[11]),
            physicsClientId=self.pybullet_client,
        )

    def _set_initial_debug_camera(self) -> None:
        if not self.gui or self.pybullet_client is None or self.scenario is None:
            return
        start = np.asarray(self.scenario.start, dtype=np.float32)
        goal = np.asarray(self.scenario.goal, dtype=np.float32)
        target = ((start + goal) * 0.5).tolist()
        target[2] = max(1.0, float(target[2]))
        distance = max(7.0, float(np.linalg.norm(goal[:2] - start[:2])) * 0.9)
        p.resetDebugVisualizerCamera(
            cameraDistance=distance,
            cameraYaw=-42,
            cameraPitch=-32,
            cameraTargetPosition=target,
            physicsClientId=self.pybullet_client,
        )

    def _configure_scene_visual_quality(self) -> None:
        if self.pybullet_client is None or not self.clean_visuals:
            return
        plane_id = getattr(self.env, "PLANE_ID", None)
        if plane_id is not None:
            p.changeVisualShape(
                int(plane_id),
                -1,
                rgbaColor=[0.88, 0.9, 0.93, 1.0],
                textureUniqueId=-1,
                physicsClientId=self.pybullet_client,
            )
        grid_extent = 6
        for value in range(-grid_extent, grid_extent + 1):
            color = [0.62, 0.66, 0.72] if value == 0 else [0.78, 0.81, 0.86]
            width = 1.4 if value == 0 else 0.6
            p.addUserDebugLine(
                [-grid_extent, value, 0.01],
                [grid_extent, value, 0.01],
                color,
                lineWidth=width,
                lifeTime=0,
                physicsClientId=self.pybullet_client,
            )
            p.addUserDebugLine(
                [value, -grid_extent, 0.01],
                [value, grid_extent, 0.01],
                color,
                lineWidth=width,
                lifeTime=0,
                physicsClientId=self.pybullet_client,
            )

    def _update_live_camera(self, position: tuple[float, float, float]) -> None:
        if not self.gui or self.pybullet_client is None or self.camera_mode != "follow":
            return
        p.resetDebugVisualizerCamera(
            cameraDistance=6.0,
            cameraYaw=-35,
            cameraPitch=-38,
            cameraTargetPosition=position,
            physicsClientId=self.pybullet_client,
        )

    def _update_drone_marker(self, position: tuple[float, float, float]) -> None:
        if self.pybullet_client is None or not self.show_drone_marker:
            return
        if self.drone_marker_body_id is None:
            self.drone_marker_body_id = self._create_marker(position, radius=0.2, color=[1.0, 0.82, 0.05, 0.9])
            self.last_marker_position = position
            return
        p.resetBasePositionAndOrientation(
            self.drone_marker_body_id,
            position,
            [0.0, 0.0, 0.0, 1.0],
            physicsClientId=self.pybullet_client,
        )
        if self.last_marker_position is not None:
            p.addUserDebugLine(
                self.last_marker_position,
                position,
                [1.0, 0.82, 0.05],
                lineWidth=2.0,
                lifeTime=0,
                physicsClientId=self.pybullet_client,
            )
        self.last_marker_position = position

    def _maybe_sample_onboard_camera(self, position: tuple[float, float, float]) -> dict[str, Any]:
        if not self.enable_onboard_camera:
            return {"enabled": False}
        should_sample = self.last_onboard_camera is None or self.step_count % self.onboard_camera_period == 0
        if should_sample:
            self.last_onboard_camera = self._sample_onboard_camera(position)
        if self.last_onboard_camera is None:
            return {"enabled": True, "available": False}
        return dict(self.last_onboard_camera)

    def _sample_onboard_camera(self, position: tuple[float, float, float]) -> dict[str, Any]:
        if self.pybullet_client is None or self.scenario is None:
            return {"enabled": True, "available": False}
        width = int(self.onboard_camera_width)
        height = int(self.onboard_camera_height)
        eye = np.asarray(position, dtype=np.float32) + np.asarray([0.0, 0.0, 0.08], dtype=np.float32)
        goal = np.asarray(self.scenario.goal, dtype=np.float32)
        direction = goal - np.asarray(position, dtype=np.float32)
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-6:
            direction = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
            norm = 1.0
        target = eye + direction / norm * 3.0
        view_matrix = p.computeViewMatrix(
            cameraEyePosition=eye.tolist(),
            cameraTargetPosition=target.tolist(),
            cameraUpVector=[0.0, 0.0, 1.0],
        )
        projection_matrix = p.computeProjectionMatrixFOV(
            fov=70.0,
            aspect=float(width) / float(height),
            nearVal=0.05,
            farVal=10.0,
        )
        renderer = p.ER_BULLET_HARDWARE_OPENGL if self.gui else p.ER_TINY_RENDERER
        _img_width, _img_height, rgba, depth, _segmentation = p.getCameraImage(
            width,
            height,
            viewMatrix=view_matrix,
            projectionMatrix=projection_matrix,
            renderer=renderer,
            physicsClientId=self.pybullet_client,
        )
        rgb_array = np.asarray(rgba, dtype=np.uint8).reshape(height, width, 4)[:, :, :3]
        depth_array = np.asarray(depth, dtype=np.float32).reshape(height, width)
        if self.gui:
            p.addUserDebugLine(
                eye.tolist(),
                target.tolist(),
                [0.0, 0.9, 1.0],
                lineWidth=2.0,
                lifeTime=0.35,
                physicsClientId=self.pybullet_client,
            )
        return {
            "enabled": True,
            "available": True,
            "width": width,
            "height": height,
            "rgb_mean": float(rgb_array.mean()),
            "depth_min": float(depth_array.min()),
            "depth_max": float(depth_array.max()),
            "eye": tuple(float(value) for value in eye),
            "target": tuple(float(value) for value in target),
        }

    def _create_marker(self, position: tuple[float, float, float], *, radius: float, color: list[float]) -> int:
        if self.pybullet_client is None:
            raise RuntimeError("PyBullet client is not available")
        visual = p.createVisualShape(
            p.GEOM_SPHERE,
            radius=radius,
            rgbaColor=color,
            specularColor=[0.25, 0.25, 0.25],
            physicsClientId=self.pybullet_client,
        )
        return int(
            p.createMultiBody(
                baseMass=0.0,
                baseCollisionShapeIndex=-1,
                baseVisualShapeIndex=visual,
                basePosition=position,
                physicsClientId=self.pybullet_client,
            )
        )

    def _create_obstacle_body(self, obstacle: ObstacleConfig, *, elapsed: float) -> int:
        if self.pybullet_client is None:
            raise RuntimeError("PyBullet client is not available")
        position = obstacle.position_at(elapsed)
        if obstacle.kind == "sphere":
            collision = p.createCollisionShape(
                p.GEOM_SPHERE,
                radius=obstacle.radius,
                physicsClientId=self.pybullet_client,
            )
            visual = p.createVisualShape(
                p.GEOM_SPHERE,
                radius=obstacle.radius,
                rgbaColor=[0.9, 0.08, 0.04, 0.92],
                specularColor=[0.35, 0.2, 0.16],
                physicsClientId=self.pybullet_client,
            )
        else:
            height = float(obstacle.height or obstacle.radius * 2.0)
            collision = p.createCollisionShape(
                p.GEOM_CYLINDER,
                radius=obstacle.radius,
                height=height,
                physicsClientId=self.pybullet_client,
            )
            visual = self._create_cylinder_visual_mesh(
                radius=float(obstacle.radius),
                height=height,
                color=[0.9, 0.08, 0.04, 0.92],
            )
        return int(
            p.createMultiBody(
                baseMass=0.0,
                baseCollisionShapeIndex=collision,
                baseVisualShapeIndex=visual,
                basePosition=position,
                physicsClientId=self.pybullet_client,
            )
        )

    def _create_cylinder_visual_mesh(self, *, radius: float, height: float, color: list[float]) -> int:
        if self.pybullet_client is None:
            raise RuntimeError("PyBullet client is not available")
        segments = 72
        half_height = height * 0.5
        vertices: list[list[float]] = []
        indices: list[int] = []
        for z in (-half_height, half_height):
            for index in range(segments):
                angle = 2.0 * np.pi * float(index) / float(segments)
                vertices.append([radius * float(np.cos(angle)), radius * float(np.sin(angle)), z])
        bottom_center = len(vertices)
        vertices.append([0.0, 0.0, -half_height])
        top_center = len(vertices)
        vertices.append([0.0, 0.0, half_height])
        for index in range(segments):
            next_index = (index + 1) % segments
            bottom_a = index
            bottom_b = next_index
            top_a = segments + index
            top_b = segments + next_index
            indices.extend([bottom_a, bottom_b, top_b])
            indices.extend([bottom_a, top_b, top_a])
            indices.extend([bottom_center, bottom_b, bottom_a])
            indices.extend([top_center, top_a, top_b])
        return int(
            p.createVisualShape(
                p.GEOM_MESH,
                vertices=vertices,
                indices=indices,
                rgbaColor=color,
                specularColor=[0.35, 0.2, 0.16],
                physicsClientId=self.pybullet_client,
            )
        )

    def _update_obstacle_bodies(self) -> None:
        if self.scenario is None or self.pybullet_client is None:
            return
        for obstacle in self.scenario.all_obstacles():
            body_id = self.obstacle_body_ids.get(obstacle.obstacle_id)
            if body_id is None:
                continue
            p.resetBasePositionAndOrientation(
                body_id,
                obstacle.position_at(self.elapsed),
                [0.0, 0.0, 0.0, 1.0],
                physicsClientId=self.pybullet_client,
            )

    def _physical_obstacle_contact(self) -> bool:
        if self.pybullet_client is None or self.drone_body_id is None:
            return False
        for body_id in self.obstacle_body_ids.values():
            contacts = p.getContactPoints(
                bodyA=self.drone_body_id,
                bodyB=body_id,
                physicsClientId=self.pybullet_client,
            )
            if contacts:
                return True
        return False
