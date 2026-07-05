#!/usr/bin/env python3
"""Render a TASK_06 case GIF or fallback summary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pirl_navrl.visualization.gif_renderer import render_task06_case_gif  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(render_task06_case_gif(args.trace, args.output))


if __name__ == "__main__":
    main()
