#!/usr/bin/env python3
"""Plot TASK_05 debug training curves from SB3 Monitor CSV logs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


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


def read_eval_summaries(run_dir: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    eval_dir = run_dir / "eval"
    if not eval_dir.exists():
        return summaries
    for path in sorted(eval_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("record_type") == "summary":
                summaries.append({"path": str(path), **record})
    return summaries


def build_summary(rows: list[dict[str, float]], eval_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "task_id": "TASK_05",
        "output_type": "diagnostic_plot_summary",
        "episodes": len(rows),
        "mean_episode_reward": sum(row["reward"] for row in rows) / len(rows),
        "mean_episode_length": sum(row["length"] for row in rows) / len(rows),
        "last_episode_reward": rows[-1]["reward"],
        "last_episode_length": rows[-1]["length"],
        "eval": [],
    }
    for summary in eval_summaries:
        payload["eval"].append(
            {
                "path": summary["path"],
                "scenario_id": summary.get("scenario_id"),
                "policy_id": summary.get("policy_id"),
                "steps": summary.get("steps"),
                "eval_final_distance": summary.get("final_distance_to_goal"),
                "min_clearance": summary.get("min_clearance"),
                "termination_status": _termination_status(summary),
                "collision": summary.get("collision"),
                "success": summary.get("success"),
                "timeout": summary.get("timeout"),
            }
        )
    return payload


def _termination_status(summary: dict[str, Any]) -> str:
    if summary.get("success"):
        return "success"
    if summary.get("collision"):
        return "collision"
    if summary.get("timeout"):
        return "timeout"
    return "unknown"


def main() -> None:
    args = parse_args()
    rows = read_monitor_rows(args.run_dir)
    if not rows:
        raise RuntimeError(f"no SB3 monitor rows found under {args.run_dir / 'logs'}")
    output = args.output or args.run_dir / "plots" / "training_curves.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path = output.with_suffix(".summary.json")
    summary = build_summary(rows, read_eval_summaries(args.run_dir))
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"matplotlib is not available; wrote summary {summary_path}")
        return
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
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
