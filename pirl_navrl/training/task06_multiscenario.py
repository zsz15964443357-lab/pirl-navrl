"""TASK_06 multi-scenario PPO diagnostic training and evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from gymnasium import spaces

from pirl_navrl.evaluation.case_selector import write_case_selection_summary
from pirl_navrl.evaluation.rollout_recorder import RolloutInitialStateRecord, RolloutJsonlWriter, RolloutStepRecord, RolloutSummary
from pirl_navrl.evaluation.reward_profiles import compute_task06_reward, get_reward_profile
from pirl_navrl.platforms.gym_pybullet_drones.feature_scaling import (
    FeatureScalingConfig,
    dynamic_obstacle_relative_features,
    navrl_style_observation,
    scale_task04_flat_observation,
    vec_from_navrl_goal_frame,
)
from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv
from pirl_navrl.scenarios.dynamic_curriculum import make_task06_scenario, task06_level_group
from pirl_navrl.training.callbacks import build_task05_callbacks
from pirl_navrl.training.vec_env import load_vecnormalize, make_dummy_vec_env, save_vecnormalize
from pirl_navrl.visualization.gif_renderer import render_task06_case_gif

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Task06TrainingConfig:
    task_id: str
    output_type: str
    scenario_group: str
    curriculum_level: str
    seed: int
    total_timesteps: int
    max_speed: float
    reward_profile: str
    output_root: Path
    run_id: str | None
    normalize_observation: bool
    normalize_reward: bool
    num_eval_episodes: int
    observation_style: str
    num_envs: int
    vec_env_type: str
    curriculum_levels: tuple[str, ...]
    ppo: dict[str, Any]
    checkpoint: dict[str, Any]
    resume_from_checkpoint: Path | None


def load_task06_training_config(path: str | Path) -> Task06TrainingConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("task_id") != "TASK_06":
        raise ValueError("TASK_06 config must use task_id='TASK_06'")
    if payload.get("output_type") != "diagnostic_training":
        raise ValueError("TASK_06 config must use output_type='diagnostic_training'")
    output_root = Path(payload["output_root"])
    if output_root.is_absolute() or not str(output_root).startswith("outputs/task06"):
        raise ValueError("TASK_06 output_root must be a relative outputs/task06 path")
    curriculum_levels = tuple(str(item) for item in payload.get("curriculum_levels", [payload["curriculum_level"]]))
    if not curriculum_levels:
        raise ValueError("TASK_06 config curriculum_levels must not be empty")
    return Task06TrainingConfig(
        task_id=payload["task_id"],
        output_type=payload["output_type"],
        scenario_group=payload["scenario_group"],
        curriculum_level=payload["curriculum_level"],
        seed=int(payload["seed"]),
        total_timesteps=int(payload["total_timesteps"]),
        max_speed=float(payload["max_speed"]),
        reward_profile=payload["reward_profile"],
        output_root=output_root,
        run_id=payload.get("run_id"),
        normalize_observation=bool(payload.get("normalize_observation", False)),
        normalize_reward=bool(payload.get("normalize_reward", False)),
        num_eval_episodes=int(payload.get("num_eval_episodes", 3)),
        observation_style=str(payload.get("observation_style", "flat")),
        num_envs=int(payload.get("num_envs", 1)),
        vec_env_type=str(payload.get("vec_env_type", "dummy")),
        curriculum_levels=curriculum_levels,
        ppo=dict(payload["ppo"]),
        checkpoint=dict(payload["checkpoint"]),
        resume_from_checkpoint=None
        if payload.get("resume_from_checkpoint") is None
        else Path(payload["resume_from_checkpoint"]),
    )


class Task06CurriculumEnv(Task04GymPybulletDronesRLEnv):
    def __init__(
        self,
        *,
        curriculum_level: str,
        seed: int,
        max_speed: float,
        reward_profile: str,
        gui: bool = False,
        curriculum_levels: tuple[str, ...] | None = None,
    ) -> None:
        self.curriculum_level = curriculum_level
        self.curriculum_levels = tuple(curriculum_levels or (curriculum_level,))
        if not self.curriculum_levels:
            raise ValueError("TASK_06 curriculum_levels must not be empty")
        self.base_seed = int(seed)
        self.episode_index = 0
        self.reward_profile_name = reward_profile
        self.scaling_config = FeatureScalingConfig(max_speed=max_speed)
        self.last_info: dict[str, Any] | None = None
        self.previous_task06_action = np.zeros(3, dtype=np.float32)
        profile = get_reward_profile(reward_profile)
        super().__init__(
            scenario=make_task06_scenario(curriculum_level, seed=seed),
            max_speed=max_speed,
            gui=gui,
            reward_config=profile.base,
        )
        self.observation_space = spaces.Box(low=-10.0, high=10.0, shape=(25,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        if seed is not None:
            self.base_seed = int(seed)
            self.episode_index = 0
        scenario_seed = self.base_seed + self.episode_index
        self.curriculum_level = self.curriculum_levels[self.episode_index % len(self.curriculum_levels)]
        self.episode_index += 1
        self.scenario = make_task06_scenario(self.curriculum_level, seed=scenario_seed)
        _obs, info = super().reset(seed=scenario_seed, options=options)
        self.previous_task06_action = np.zeros(3, dtype=np.float32)
        self.observation_space = spaces.Box(low=-10.0, high=10.0, shape=(25,), dtype=np.float32)
        obs = self._task06_observation()
        info = {**info, **self._task06_info_fields()}
        self.last_info = info
        return obs, info

    def step(self, action):
        if self.adapter is None or self.previous_obs_dict is None:
            raise RuntimeError("reset() must be called before step()")
        normalized_action = np.clip(np.asarray(action, dtype=np.float32).reshape(3), -1.0, 1.0)
        desired_velocity = normalized_action * float(self.max_speed)
        current_obs_dict, _platform_reward, terminated, truncated, info = self.adapter.step(desired_velocity)
        event_flags = {
            "collision": bool(info["collision"]),
            "success": bool(info["success"]),
            "timeout": bool(info["timeout"]),
        }
        dynamic_features = self._dynamic_features(current_obs_dict)
        reward, reward_terms = compute_task06_reward(
            self.previous_obs_dict,
            current_obs_dict,
            normalized_action,
            event_flags,
            profile_name=self.reward_profile_name,
            dynamic_relative_velocity=dynamic_features[3:6],
            previous_action=self.previous_task06_action,
        )
        self.previous_task06_action = normalized_action.astype(np.float32)
        self.previous_obs_dict = current_obs_dict
        obs = self._task06_observation(current_obs_dict)
        info = {**info, "reward_terms": reward_terms, **self._task06_info_fields(current_obs_dict)}
        self.last_info = info
        return obs, float(reward), bool(terminated), bool(truncated), info

    def _task06_observation(self, obs_dict: dict[str, Any] | None = None) -> np.ndarray:
        current = obs_dict or self.previous_obs_dict
        if current is None:
            raise RuntimeError("reset() must be called before building TASK_06 observation")
        base = scale_task04_flat_observation(current, self.scaling_config)
        dynamic = self._dynamic_features(current)
        return np.concatenate([base, dynamic], dtype=np.float32)

    def _dynamic_features(self, obs_dict: dict[str, Any]) -> np.ndarray:
        elapsed = 0.0 if self.adapter is None else float(self.adapter.elapsed)
        return dynamic_obstacle_relative_features(
            scenario=self.scenario,
            position=obs_dict["position"],
            velocity=obs_dict["velocity"],
            elapsed=elapsed,
            config=self.scaling_config,
        )

    def _task06_info_fields(self, obs_dict: dict[str, Any] | None = None) -> dict[str, Any]:
        current = obs_dict or self.previous_obs_dict
        elapsed = 0.0 if self.adapter is None else float(self.adapter.elapsed)
        dynamic_positions = [
            tuple(float(v) for v in obstacle.position_at(elapsed))
            for obstacle in self.scenario.dynamic_obstacles
        ]
        dynamic_velocities = [
            tuple(float(v) for v in (obstacle.velocity or (0.0, 0.0, 0.0)))
            if elapsed > obstacle.start_time
            else (0.0, 0.0, 0.0)
            for obstacle in self.scenario.dynamic_obstacles
        ]
        return {
            "task06_observation_shape": (25,),
            "curriculum_level": self.curriculum_level,
            "curriculum_levels": self.curriculum_levels,
            "goal": self.scenario.goal,
            "dynamic_obstacle_positions": dynamic_positions,
            "dynamic_obstacle_velocities": dynamic_velocities,
            "dynamic_relative_features": tuple(float(v) for v in self._dynamic_features(current)) if current is not None else (),
            "elapsed": elapsed,
        }


class Task06NavRLStyleEnv(Task06CurriculumEnv):
    def __init__(
        self,
        *,
        curriculum_level: str,
        seed: int,
        max_speed: float,
        reward_profile: str,
        gui: bool = False,
        curriculum_levels: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(
            curriculum_level=curriculum_level,
            seed=seed,
            max_speed=max_speed,
            reward_profile=reward_profile,
            gui=gui,
            curriculum_levels=curriculum_levels,
        )
        self.observation_space = _navrl_style_observation_space()

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        _obs, info = super().reset(seed=seed, options=options)
        self.observation_space = _navrl_style_observation_space()
        return self._task06_observation(), info

    def step(self, action):
        if self.adapter is None or self.previous_obs_dict is None:
            raise RuntimeError("reset() must be called before step()")
        goal_frame_action = np.clip(np.asarray(action, dtype=np.float32).reshape(3), -1.0, 1.0)
        relative_goal = np.asarray(self.previous_obs_dict["relative_goal"], dtype=np.float32).reshape(3)
        world_action = vec_from_navrl_goal_frame(goal_frame_action, relative_goal)
        world_norm = float(np.linalg.norm(world_action))
        if world_norm > 1.0:
            world_action = world_action / world_norm
        desired_velocity = world_action * float(self.max_speed)
        current_obs_dict, _platform_reward, terminated, truncated, info = self.adapter.step(desired_velocity)
        event_flags = {
            "collision": bool(info["collision"]),
            "success": bool(info["success"]),
            "timeout": bool(info["timeout"]),
        }
        dynamic_features = self._dynamic_features(current_obs_dict)
        reward, reward_terms = compute_task06_reward(
            self.previous_obs_dict,
            current_obs_dict,
            world_action,
            event_flags,
            profile_name=self.reward_profile_name,
            dynamic_relative_velocity=dynamic_features[3:6],
            previous_action=self.previous_task06_action,
        )
        self.previous_task06_action = world_action.astype(np.float32)
        self.previous_obs_dict = current_obs_dict
        obs = self._task06_observation(current_obs_dict)
        info = {
            **info,
            "reward_terms": reward_terms,
            "navrl_goal_frame_action": tuple(float(v) for v in goal_frame_action),
            "navrl_world_action": tuple(float(v) for v in world_action),
            **self._task06_info_fields(current_obs_dict),
        }
        self.last_info = info
        return obs, float(reward), bool(terminated), bool(truncated), info

    def _task06_observation(self, obs_dict: dict[str, Any] | None = None) -> dict[str, np.ndarray]:
        current = obs_dict or self.previous_obs_dict
        if current is None:
            raise RuntimeError("reset() must be called before building TASK_06 observation")
        elapsed = 0.0 if self.adapter is None else float(self.adapter.elapsed)
        pybullet_client = None if self.adapter is None else self.adapter.pybullet_client
        ignore_body_ids: set[int] = set()
        if self.adapter is not None and self.adapter.drone_body_id is not None:
            ignore_body_ids.add(int(self.adapter.drone_body_id))
        return navrl_style_observation(
            obs_dict=current,
            scenario=self.scenario,
            elapsed=elapsed,
            config=self.scaling_config,
            pybullet_client=pybullet_client,
            ignore_body_ids=ignore_body_ids,
        )

    def _task06_info_fields(self, obs_dict: dict[str, Any] | None = None) -> dict[str, Any]:
        info = super()._task06_info_fields(obs_dict)
        info["task06_observation_style"] = "navrl_style"
        info["task06_lidar_source"] = "pybullet_raycast" if self.adapter is not None and self.adapter.pybullet_client is not None else "scenario_geometry_fallback"
        info["task06_observation_shape"] = {
            "state": (8,),
            "lidar": (1, 36, 4),
            "direction": (1, 3),
            "dynamic_obstacle": (1, 5, 10),
        }
        return info


def _navrl_style_observation_space() -> spaces.Dict:
    return spaces.Dict(
        {
            "state": spaces.Box(low=-10.0, high=10.0, shape=(8,), dtype=np.float32),
            "lidar": spaces.Box(low=0.0, high=1.0, shape=(1, 36, 4), dtype=np.float32),
            "direction": spaces.Box(low=-1.0, high=1.0, shape=(1, 3), dtype=np.float32),
            "dynamic_obstacle": spaces.Box(low=-10.0, high=10.0, shape=(1, 5, 10), dtype=np.float32),
        }
    )


def make_task06_env(
    *,
    curriculum_level: str,
    seed: int,
    max_speed: float,
    reward_profile: str,
    gui: bool = False,
    observation_style: str = "flat",
    curriculum_levels: tuple[str, ...] | None = None,
) -> Task06CurriculumEnv:
    env_class = Task06NavRLStyleEnv if observation_style == "navrl_style" else Task06CurriculumEnv
    if observation_style not in {"flat", "navrl_style"}:
        raise ValueError("TASK_06 observation_style must be 'flat' or 'navrl_style'")
    return env_class(
        curriculum_level=curriculum_level,
        seed=seed,
        max_speed=max_speed,
        reward_profile=reward_profile,
        gui=gui,
        curriculum_levels=curriculum_levels,
    )


def train_task06_multiscenario(config_path: str | Path) -> Path:
    from stable_baselines3 import PPO
    from stable_baselines3.common.monitor import Monitor

    config = load_task06_training_config(config_path)
    run_id = config.run_id or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{config.scenario_group}_{config.curriculum_level}_seed{config.seed}"
    run_dir = ROOT_DIR / config.output_root / run_id
    checkpoint_dir = run_dir / "checkpoints"
    log_dir = run_dir / "logs"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    if config.num_envs < 1:
        raise ValueError("TASK_06 num_envs must be >= 1")

    def make_env_fn(rank: int):
        def env_fn():
            env_seed = config.seed + rank * 100_000
            return Monitor(
                make_task06_env(
                    curriculum_level=config.curriculum_level,
                    curriculum_levels=config.curriculum_levels,
                    seed=env_seed,
                    max_speed=config.max_speed,
                    reward_profile=config.reward_profile,
                    observation_style=config.observation_style,
                ),
                filename=str(log_dir / f"monitor_env{rank}.csv"),
            )

        return env_fn

    env_fns = [make_env_fn(rank) for rank in range(config.num_envs)]
    vec_env = make_dummy_vec_env(
        env_fns,
        normalize_observation=config.normalize_observation,
        normalize_reward=config.normalize_reward,
        vec_env_type=config.vec_env_type,
    )
    ppo_params = dict(config.ppo)
    feature_extractor = ppo_params.pop("feature_extractor", None)
    if feature_extractor == "navrl_style":
        from pirl_navrl.training.navrl_style_policy import NavRLStyleFeatureExtractor

        policy_kwargs = dict(ppo_params.pop("policy_kwargs", {}))
        policy_kwargs["features_extractor_class"] = NavRLStyleFeatureExtractor
        policy_kwargs.setdefault("features_extractor_kwargs", {"features_dim": 256})
        policy_kwargs.setdefault("net_arch", {"pi": [256, 128], "vf": [256, 128]})
        ppo_params["policy_kwargs"] = policy_kwargs
    elif feature_extractor is not None:
        raise ValueError(f"unknown TASK_06 feature_extractor {feature_extractor!r}")
    policy = ppo_params.pop("policy", "MlpPolicy")
    if config.resume_from_checkpoint is None:
        model = PPO(policy, vec_env, seed=config.seed, **ppo_params)
    else:
        model = PPO.load(str(config.resume_from_checkpoint), env=vec_env, seed=config.seed, device=ppo_params.get("device", "auto"))
    reset_num_timesteps = True
    callbacks = build_task05_callbacks(
        checkpoint_dir=checkpoint_dir,
        save_freq=int(config.checkpoint.get("save_freq", 0)),
        name_prefix=str(config.checkpoint.get("name_prefix", "task06_ppo_debug")),
        total_timesteps=config.total_timesteps,
        progress_log_freq=int(config.checkpoint.get("progress_log_freq", 50_000)),
    )
    resolved_config = {
        **config.__dict__,
        "output_root": str(config.output_root),
        "resume_from_checkpoint": None if config.resume_from_checkpoint is None else str(config.resume_from_checkpoint),
    }
    (run_dir / "resolved_config.json").write_text(json.dumps(resolved_config, indent=2, sort_keys=True), encoding="utf-8")
    try:
        model.learn(total_timesteps=config.total_timesteps, callback=callbacks, reset_num_timesteps=reset_num_timesteps)
        model.save(str(checkpoint_dir / "final_model.zip"))
        save_vecnormalize(vec_env, str(checkpoint_dir / "vecnormalize.pkl"))
    finally:
        vec_env.close()
    vecnormalize_path = checkpoint_dir / "vecnormalize.pkl"
    if not vecnormalize_path.exists():
        vecnormalize_path = None
    random_summary = run_task06_batch_eval(
        curriculum_level=config.curriculum_level,
        output_dir=run_dir / "eval" / "random",
        num_episodes=config.num_eval_episodes,
        seed=config.seed + 10_000,
        random_policy=True,
        max_speed=config.max_speed,
        reward_profile=config.reward_profile,
        observation_style=config.observation_style,
        render_gifs=True,
    )
    trained_summary = run_task06_batch_eval(
        curriculum_level=config.curriculum_level,
        output_dir=run_dir / "eval" / "trained",
        num_episodes=config.num_eval_episodes,
        seed=config.seed + 20_000,
        checkpoint_path=checkpoint_dir / "final_model.zip",
        vecnormalize_path=vecnormalize_path,
        max_speed=config.max_speed,
        reward_profile=config.reward_profile,
        observation_style=config.observation_style,
        render_gifs=True,
    )
    effect = compare_task06_summaries(random_summary, trained_summary)
    comparison = {
        "task_id": "TASK_06",
        "output_type": "diagnostic_training_comparison",
        "scenario_group": config.scenario_group,
        "curriculum_level": config.curriculum_level,
        "reward_profile": config.reward_profile,
        "max_speed": config.max_speed,
        "num_envs": config.num_envs,
        "debug_learning_effect": effect,
        "random_policy_summary": random_summary,
        "trained_policy_summary": trained_summary,
        "notes": "Diagnostic only; not a formal baseline or success-rate report.",
    }
    (run_dir / "random_vs_trained_summary.json").write_text(json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8")
    return run_dir


def run_task06_eval(
    *,
    curriculum_level: str,
    seed: int,
    output_path: str | Path,
    checkpoint_path: str | Path | None = None,
    vecnormalize_path: str | Path | None = None,
    random_policy: bool = False,
    max_speed: float = 1.0,
    reward_profile: str | None = None,
    gui: bool = False,
    observation_style: str = "flat",
) -> Path:
    if checkpoint_path is not None and random_policy:
        raise ValueError("choose checkpoint_path or random_policy, not both")
    model = None
    if checkpoint_path is not None:
        from stable_baselines3 import PPO

        model = PPO.load(str(checkpoint_path))
    policy_id = "random_policy_debug" if model is None else "task06_ppo_checkpoint"
    scenario = make_task06_scenario(curriculum_level, seed=seed)
    env = make_task06_env(
        curriculum_level=curriculum_level,
        seed=seed,
        max_speed=max_speed,
        reward_profile=reward_profile or _reward_profile_for_level(curriculum_level),
        gui=gui,
        observation_style=observation_style,
    )
    output = Path(output_path)
    if not output.is_absolute():
        output = ROOT_DIR / output
    vec_env = None
    if model is not None and vecnormalize_path is not None:
        from stable_baselines3.common.vec_env import DummyVecEnv

        vec_env = DummyVecEnv([lambda: env])
        vec_env = load_vecnormalize(str(vecnormalize_path), vec_env)
        vec_env.training = False
        vec_env.norm_reward = False
        obs = vec_env.reset()
        info = env.last_info or {}
    else:
        obs, info = env.reset(seed=seed)
    min_clearance = float(info["min_clearance"])
    last_info = info
    metadata = {
        "task_id": "TASK_06",
        "output_type": "diagnostic",
        "route": "task06_multiscenario_eval",
        "scenario_group": task06_level_group(curriculum_level),
        "curriculum_level": curriculum_level,
        "policy_id": policy_id,
        "checkpoint_path": None if checkpoint_path is None else str(checkpoint_path),
        "vecnormalize_path": None if vecnormalize_path is None else str(vecnormalize_path),
        "scenario": scenario.to_dict(),
        "observation_style": observation_style,
        "reward_profile": reward_profile or _reward_profile_for_level(curriculum_level),
        "max_speed": max_speed,
    }
    try:
        with RolloutJsonlWriter(output, metadata) as writer:
            writer.write_initial_state(
                RolloutInitialStateRecord(
                    task_id="TASK_06",
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
                action = env.action_space.sample() if model is None else model.predict(obs, deterministic=True)[0]
                if vec_env is not None:
                    vec_obs, _rewards, dones, infos = vec_env.step(np.asarray([action], dtype=np.float32))
                    obs = vec_obs
                    info = dict(infos[0])
                    terminated = bool(info["success"] or info["collision"])
                    truncated = bool(info["timeout"] or dones[0])
                else:
                    obs, _reward, terminated, truncated, info = env.step(np.asarray(action, dtype=np.float32))
                min_clearance = min(min_clearance, float(info["min_clearance"]))
                recorded_action = info.get("applied_action", action)
                writer.write_step(
                    RolloutStepRecord(
                        task_id="TASK_06",
                        output_type="diagnostic",
                        platform_id=info["platform_id"],
                        scenario_id=info["scenario_id"],
                        seed=int(info["seed"]),
                        policy_id=policy_id,
                        step=step_index + 1,
                        position=tuple(info["position"]),
                        velocity=tuple(info["velocity"]),
                        goal=scenario.goal,
                        action=tuple(float(v) for v in np.asarray(recorded_action, dtype=np.float32).reshape(3)),
                        distance_to_goal=float(info["distance_to_goal"]),
                        min_clearance=float(info["min_clearance"]),
                        collision=bool(info["collision"]),
                        success=bool(info["success"]),
                        timeout=bool(info["timeout"]),
                        elapsed=float(info.get("elapsed", 0.0)),
                        dynamic_obstacle_positions=info.get("dynamic_obstacle_positions", []),
                        dynamic_obstacle_velocities=info.get("dynamic_obstacle_velocities", []),
                        dynamic_relative_features=info.get("dynamic_relative_features", []),
                    )
                )
                last_info = info
                if terminated or truncated:
                    break
            summary = RolloutSummary(
                task_id="TASK_06",
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
    finally:
        if vec_env is not None:
            vec_env.close()
        else:
            env.close()
    return output


def select_cases_for_run(trace_paths: list[str | Path], output_path: str | Path) -> Path:
    return write_case_selection_summary(trace_paths, output_path)


def run_task06_batch_eval(
    *,
    curriculum_level: str,
    output_dir: str | Path,
    num_episodes: int,
    seed: int,
    checkpoint_path: str | Path | None = None,
    vecnormalize_path: str | Path | None = None,
    random_policy: bool = False,
    max_speed: float = 1.0,
    reward_profile: str | None = None,
    observation_style: str = "flat",
    render_gifs: bool = True,
) -> dict[str, Any]:
    from pirl_navrl.analysis.rollout_metrics import aggregate_rollout_metrics
    from pirl_navrl.evaluation.case_selector import select_task06_cases

    output = Path(output_dir)
    if not output.is_absolute():
        output = ROOT_DIR / output
    output.mkdir(parents=True, exist_ok=True)
    trace_paths: list[Path] = []
    for episode_index in range(int(num_episodes)):
        trace_path = output / f"episode_{episode_index:03d}.jsonl"
        run_task06_eval(
            curriculum_level=curriculum_level,
            seed=seed + episode_index,
            output_path=trace_path,
            checkpoint_path=checkpoint_path,
            vecnormalize_path=vecnormalize_path,
            random_policy=random_policy,
            max_speed=max_speed,
            reward_profile=reward_profile,
            observation_style=observation_style,
        )
        trace_paths.append(trace_path)
    scenario_group = task06_level_group(curriculum_level)
    summary = aggregate_rollout_metrics(
        trace_paths,
        scenario_group=scenario_group,
        checkpoint=None if checkpoint_path is None else str(checkpoint_path),
    )
    summary["policy_id"] = "random_policy_debug" if random_policy or checkpoint_path is None else "task06_ppo_checkpoint"
    summary["debug_learning_effect"] = "pending_comparison"
    summary["reward_profile"] = reward_profile or _reward_profile_for_level(curriculum_level)
    summary["max_speed"] = max_speed
    cases = select_task06_cases(trace_paths)
    cases_dir = output / "cases" / scenario_group
    cases_dir.mkdir(parents=True, exist_ok=True)
    case_selection_path = cases_dir / "case_selection_summary.json"
    case_selection_path.write_text(json.dumps(cases, indent=2, sort_keys=True), encoding="utf-8")
    _write_case_artifact(cases["best_case"], cases_dir, render_gifs=render_gifs)
    _write_case_artifact(cases["failure_case"], cases_dir, render_gifs=render_gifs)
    summary["best_case_trace"] = cases["best_case"]["trace_path"]
    summary["failure_case_trace"] = cases["failure_case"]["trace_path"]
    summary["case_selection_summary"] = str(case_selection_path)
    summary_path = output / ("random_policy_summary.json" if summary["policy_id"] == "random_policy_debug" else "trained_policy_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def compare_task06_summaries(random_summary: dict[str, Any], trained_summary: dict[str, Any]) -> str:
    if trained_summary.get("success_count", 0) > random_summary.get("success_count", 0):
        return "improved_success_count"
    random_distance = random_summary.get("mean_final_distance")
    trained_distance = trained_summary.get("mean_final_distance")
    if random_distance is not None and trained_distance is not None and float(trained_distance) < float(random_distance):
        return "improved_final_distance"
    random_collision = random_summary.get("collision_count", 0)
    trained_collision = trained_summary.get("collision_count", 0)
    if trained_collision < random_collision:
        return "improved_collision_count"
    return "improved_not_observed"


def _write_case_artifact(case: dict[str, Any], cases_dir: Path, *, render_gifs: bool) -> None:
    case_type = str(case["case_type"])
    trace_path = Path(case["trace_path"])
    jsonl_output = cases_dir / f"{case_type}.jsonl"
    jsonl_output.write_text(trace_path.read_text(encoding="utf-8"), encoding="utf-8")
    summary_output = cases_dir / f"{case_type}_summary.json"
    summary_output.write_text(json.dumps(case, indent=2, sort_keys=True), encoding="utf-8")
    if render_gifs:
        render_task06_case_gif(jsonl_output, cases_dir / f"{case_type}.gif")


def _reward_profile_for_level(curriculum_level: str) -> str:
    group = task06_level_group(curriculum_level)
    if group == "static":
        return "static_avoidance"
    if group == "dynamic":
        return "dynamic_avoidance"
    if group == "latent_dynamic":
        return "latent_risk"
    return "dynamic_avoidance"
