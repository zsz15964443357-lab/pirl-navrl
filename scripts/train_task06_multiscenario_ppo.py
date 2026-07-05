#!/usr/bin/env python3
"""Run TASK_06 multi-scenario PPO diagnostic training."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.training.task06_multiscenario import train_task06_multiscenario  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    run_dir = train_task06_multiscenario(parse_args().config)
    print(f"TASK_06 run_dir={run_dir}")


if __name__ == "__main__":
    main()
