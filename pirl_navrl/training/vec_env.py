"""Vectorized env helpers for TASK_06 diagnostic training."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Callable


def make_dummy_vec_env(
    env_fn: Callable | Sequence[Callable],
    *,
    normalize_observation: bool = False,
    normalize_reward: bool = False,
    vec_env_type: str = "dummy",
):
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize

    env_fns = list(env_fn) if isinstance(env_fn, Sequence) else [env_fn]
    if not env_fns:
        raise ValueError("make_dummy_vec_env requires at least one env function")
    if vec_env_type == "dummy":
        vec_env = DummyVecEnv(env_fns)
    elif vec_env_type == "subproc":
        vec_env = SubprocVecEnv(env_fns, start_method="fork")
    else:
        raise ValueError("vec_env_type must be one of: dummy, subproc")
    if normalize_observation or normalize_reward:
        return VecNormalize(vec_env, norm_obs=normalize_observation, norm_reward=normalize_reward)
    return vec_env


def save_vecnormalize(vec_env, path: str) -> None:
    if hasattr(vec_env, "save"):
        vec_env.save(path)


def load_vecnormalize(path: str, vec_env):
    from stable_baselines3.common.vec_env import VecNormalize

    return VecNormalize.load(path, vec_env)
