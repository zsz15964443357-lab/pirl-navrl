#!/usr/bin/env python3
"""Plot TASK_05 debug training curves from SB3 Monitor CSV logs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def read_monitor_rows(run_dir: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for path in sorted((run_dir / "logs").glob("*monitor.csv")):
        with path.open("r", encoding="utf-8") as handle:
            filtered = [line for line in handle if not line.startswith("#")]
        for row in csv.DictReader(filtered):
            rows.append({"reward": float(row["r"]), "length": float(row["l"]), "time": float(row["t"])})
    return rows


def main() -> None:
    args = parse_args()
    rows = read_monitor_rows(args.run_dir)
    if not rows:
        raise RuntimeError(f"no SB3 monitor rows found under {args.run_dir / 'logs'}")
    output = args.output or args.run_dir / "plots" / "training_curves.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        summary = {
            "episodes": len(rows),
            "mean_reward": sum(row["reward"] for row in rows) / len(rows),
            "mean_length": sum(row["length"] for row in rows) / len(rows),
        }
        fallback = output.with_suffix(".json")
        fallback.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        raise RuntimeError(f"matplotlib is not available; wrote summary to {fallback}") from exc
    xs = list(range(1, len(rows) + 1))
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axes[0].plot(xs, [row["reward"] for row in rows], color="#1f77b4")
    axes[0].set_ylabel("episode reward")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(xs, [row["length"] for row in rows], color="#2ca02c")
    axes[1].set_ylabel("episode length")
    axes[1].set_xlabel("episode")
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
