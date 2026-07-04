#!/usr/bin/env python3
"""Run a TASK_05 debug policy evaluation rollout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.training.eval import run_task05_eval  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--curriculum-level", default="level_0_no_obstacle_short")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-speed", type=float, default=1.0)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--deterministic", action="store_true", default=True)
    parser.add_argument("--stochastic", dest="deterministic", action="store_false")
    parser.add_argument("--random-policy", action="store_true")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--realtime", action="store_true", help="Sleep between steps during evaluation playback.")
    parser.add_argument(
        "--hold-seconds",
        type=float,
        help="Seconds to keep GUI open after playback. Omit with --gui to keep it open until closed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_task05_eval(
        checkpoint_path=args.checkpoint,
        output_path=args.output,
        curriculum_level=args.curriculum_level,
        seed=args.seed,
        max_speed=args.max_speed,
        gui=args.gui,
        deterministic=args.deterministic,
        max_steps=args.max_steps,
        random_policy=args.random_policy or args.checkpoint is None,
        realtime=args.realtime,
        hold_seconds=args.hold_seconds,
    )


if __name__ == "__main__":
    main()
