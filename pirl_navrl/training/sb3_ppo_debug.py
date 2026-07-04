"""Stable-Baselines3 PPO debug training for TASK_05."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import gymnasium as gym

from pirl_navrl.platforms.gym_pybullet_drones.rl_env import Task04GymPybulletDronesRLEnv
from pirl_navrl.scenarios.curriculum import make_curriculum_scenario
from pirl_navrl.training.callbacks import build_task05_callbacks

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Task05TrainingConfig:
    task_id: str
    output_type: str
    curriculum_level: str
    seed: int
    total_timesteps: int
    max_speed: float
    output_root: Path
    run_id: str | None
    randomize_each_reset: bool
    gui: bool
    ppo: dict[str, Any]
    checkpoint: dict[str, Any]


def load_training_config(path: str | Path) -> Task05TrainingConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("task_id") != "TASK_05":
        raise ValueError("TASK_05 training config must use task_id='TASK_05'")
    if payload.get("output_type") != "diagnostic_training":
        raise ValueError("TASK_05 training config must use output_type='diagnostic_training'")
    output_root = Path(payload["output_root"])
    if output_root.is_absolute() or not str(output_root).startswith("outputs/task05"):
        raise ValueError("TASK_05 debug training output_root must be a relative outputs/task05 path")
    return Task05TrainingConfig(
        task_id=payload["task_id"],
        output_type=payload["output_type"],
        curriculum_level=payload["curriculum_level"],
        seed=int(payload["seed"]),
        total_timesteps=int(payload["total_timesteps"]),
        max_speed=float(payload["max_speed"]),
        output_root=output_root,
        run_id=payload.get("run_id"),
        randomize_each_reset=bool(payload.get("randomize_each_reset", True)),
        gui=bool(payload.get("gui", False)),
        ppo=dict(payload["ppo"]),
        checkpoint=dict(payload["checkpoint"]),
    )


class Task05CurriculumEnv(gym.Env):
    """Gym wrapper that regenerates a seeded TASK_05 scenario on reset."""

    metadata = Task04GymPybulletDronesRLEnv.metadata

    def __init__(
        self,
        *,
        curriculum_level: str,
        seed: int,
        max_speed: float,
        randomize_each_reset: bool = True,
        gui: bool = False,
    ) -> None:
        super().__init__()
        self.curriculum_level = curriculum_level
        self.base_seed = int(seed)
        self.episode_index = 0
        self.randomize_each_reset = randomize_each_reset
        scenario = make_curriculum_scenario(curriculum_level, seed=self.base_seed)
        self.inner = Task04GymPybulletDronesRLEnv(
            scenario=scenario,
            max_speed=max_speed,
            gui=gui,
            camera_mode="manual",
            camera_control="orbit",
        )
        self.observation_space = self.inner.observation_space
        self.action_space = self.inner.action_space

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        del options
        if seed is not None:
            self.base_seed = int(seed)
            self.episode_index = 0
        scenario_seed = self.base_seed
        if self.randomize_each_reset:
            scenario_seed = self.base_seed + self.episode_index
        self.episode_index += 1
        self.inner.scenario = make_curriculum_scenario(self.curriculum_level, seed=scenario_seed)
        self.observation_space = self.inner.observation_space
        return self.inner.reset(seed=scenario_seed)

    def step(self, action):
        return self.inner.step(action)

    def render(self):
        return self.inner.render()

    def close(self) -> None:
        self.inner.close()


def make_task05_env(
    *,
    curriculum_level: str,
    seed: int,
    max_speed: float,
    randomize_each_reset: bool = True,
    gui: bool = False,
) -> Task05CurriculumEnv:
    return Task05CurriculumEnv(
        curriculum_level=curriculum_level,
        seed=seed,
        max_speed=max_speed,
        randomize_each_reset=randomize_each_reset,
        gui=gui,
    )


def _run_id(config: Task05TrainingConfig) -> str:
    if config.run_id:
        return config.run_id
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{config.curriculum_level}_seed{config.seed}"


def train_ppo_debug(config_path: str | Path) -> Path:
    """Run a small PPO debug training job and return the run directory."""

    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.monitor import Monitor
    except ImportError as exc:
        raise RuntimeError("stable-baselines3 is required for TASK_05 PPO debug training") from exc

    config = load_training_config(config_path)
    run_dir = ROOT_DIR / config.output_root / _run_id(config)
    checkpoint_dir = run_dir / "checkpoints"
    log_dir = run_dir / "logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    env = make_task05_env(
        curriculum_level=config.curriculum_level,
        seed=config.seed,
        max_speed=config.max_speed,
        randomize_each_reset=config.randomize_each_reset,
        gui=config.gui,
    )
    monitored_env = Monitor(env, filename=str(log_dir / "monitor.csv"))
    ppo_params = dict(config.ppo)
    policy = ppo_params.pop("policy", "MlpPolicy")
    model = PPO(policy, monitored_env, seed=config.seed, **ppo_params)
    callbacks = build_task05_callbacks(
        checkpoint_dir=checkpoint_dir,
        save_freq=int(config.checkpoint.get("save_freq", 0)),
        name_prefix=str(config.checkpoint.get("name_prefix", "task05_ppo_debug")),
    )
    resolved = {
        "task_id": config.task_id,
        "output_type": config.output_type,
        "config_path": str(config_path),
        "run_dir": str(run_dir),
        "curriculum_level": config.curriculum_level,
        "seed": config.seed,
        "total_timesteps": config.total_timesteps,
        "max_speed": config.max_speed,
        "randomize_each_reset": config.randomize_each_reset,
        "ppo": config.ppo,
        "checkpoint": config.checkpoint,
    }
    (run_dir / "resolved_config.json").write_text(json.dumps(resolved, indent=2, sort_keys=True), encoding="utf-8")
    try:
        model.learn(total_timesteps=config.total_timesteps, callback=callbacks)
        model.save(str(checkpoint_dir / "final_model.zip"))
    finally:
        monitored_env.close()
    return run_dir
