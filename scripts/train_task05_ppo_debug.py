#!/usr/bin/env python3
"""Run TASK_05 SB3 PPO debug training."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.training.sb3_ppo_debug import train_ppo_debug  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT_DIR / "configs/task05_ppo_debug_train.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = train_ppo_debug(args.config)
    print(f"TASK_05 debug training run_dir={run_dir}")


if __name__ == "__main__":
    main()
