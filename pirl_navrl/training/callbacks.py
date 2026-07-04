"""Stable-Baselines3 callback helpers for TASK_05 debug training."""

from __future__ import annotations

from pathlib import Path


def build_task05_callbacks(*, checkpoint_dir: Path, save_freq: int, name_prefix: str):
    """Build a small callback list without importing SB3 at package import time."""

    from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    callbacks = []
    if save_freq > 0:
        callbacks.append(
            CheckpointCallback(
                save_freq=int(save_freq),
                save_path=str(checkpoint_dir),
                name_prefix=name_prefix,
                save_replay_buffer=False,
                save_vecnormalize=False,
            )
        )
    return CallbackList(callbacks)
