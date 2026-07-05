#!/usr/bin/env python3
"""Run TASK_06 multi-scenario diagnostic eval."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.analysis.rollout_metrics import compute_rollout_metrics  # noqa: E402
from pirl_navrl.training.task06_multiscenario import run_task06_batch_eval, run_task06_eval  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curriculum-level", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--vecnormalize", type=Path)
    parser.add_argument("--random-policy", action="store_true")
    parser.add_argument("--max-speed", type=float, default=1.0)
    parser.add_argument("--reward-profile")
    parser.add_argument("--observation-style", choices=["flat", "navrl_style"], default="flat")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--render-gifs", action="store_true")
    parser.add_argument("--gui", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.episodes > 1:
        summary = run_task06_batch_eval(
            curriculum_level=args.curriculum_level,
            seed=args.seed,
            output_dir=args.output,
            num_episodes=args.episodes,
            checkpoint_path=args.checkpoint,
            vecnormalize_path=args.vecnormalize,
            random_policy=args.random_policy or args.checkpoint is None,
            max_speed=args.max_speed,
            reward_profile=args.reward_profile,
            observation_style=args.observation_style,
            render_gifs=args.render_gifs,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    output = run_task06_eval(
        curriculum_level=args.curriculum_level,
        seed=args.seed,
        output_path=args.output,
        checkpoint_path=args.checkpoint,
        vecnormalize_path=args.vecnormalize,
        random_policy=args.random_policy or args.checkpoint is None,
        max_speed=args.max_speed,
        reward_profile=args.reward_profile,
        observation_style=args.observation_style,
        gui=args.gui,
    )
    print(json.dumps(compute_rollout_metrics(output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
