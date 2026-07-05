"""Stable-Baselines3 callback helpers for TASK_05 debug training."""

from __future__ import annotations

import time
from pathlib import Path


def build_task05_callbacks(
    *,
    checkpoint_dir: Path,
    save_freq: int,
    name_prefix: str,
    total_timesteps: int | None = None,
    progress_log_freq: int = 0,
):
    """Build a small callback list without importing SB3 at package import time."""

    from stable_baselines3.common.callbacks import BaseCallback, CallbackList, CheckpointCallback

    class ProgressCallback(BaseCallback):
        def __init__(self, *, total_timesteps: int, log_freq: int) -> None:
            super().__init__()
            self.total_timesteps = max(1, int(total_timesteps))
            self.log_freq = max(1, int(log_freq))
            self.started_at = 0.0
            self.last_logged = 0

        def _on_training_start(self) -> None:
            self.started_at = time.monotonic()
            self.last_logged = 0
            print(
                f"[progress] step=0/{self.total_timesteps} pct=0.0 elapsed=0.0m eta=unknown",
                flush=True,
            )

        def _on_step(self) -> bool:
            current = int(self.num_timesteps)
            if current < self.total_timesteps and current - self.last_logged < self.log_freq:
                return True
            elapsed = max(time.monotonic() - self.started_at, 1e-6)
            fps = current / elapsed
            remaining = max(self.total_timesteps - current, 0)
            eta_seconds = remaining / max(fps, 1e-6)
            pct = min(100.0, 100.0 * current / self.total_timesteps)
            print(
                "[progress] "
                f"step={current}/{self.total_timesteps} "
                f"pct={pct:.1f} "
                f"fps={fps:.1f} "
                f"elapsed={elapsed / 60.0:.1f}m "
                f"eta={eta_seconds / 60.0:.1f}m",
                flush=True,
            )
            self.last_logged = current
            return True

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    callbacks = []
    if total_timesteps is not None and progress_log_freq > 0:
        callbacks.append(ProgressCallback(total_timesteps=int(total_timesteps), log_freq=int(progress_log_freq)))
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
