# TASK_05 Completion Report

## Scope

TASK_05 implemented the first NavRL-informed PPO debug training chain for
PIRL-NavRL. This stage is diagnostic only. It is not a baseline, not a formal
experiment, and does not report official success rate or paper metrics.

## Completed Work

- Reviewed NavRL training-related code and documented reference boundaries in
  `docs/navrl_code_review_for_task05.md`.
- Reviewed TASK_03/TASK_04 readiness for SB3-style training in
  `docs/task05_training_readiness_review.md`.
- Added seeded curriculum scenario generation:
  `pirl_navrl/scenarios/curriculum.py`.
- Added three curriculum levels in `configs/task05_curriculum_levels.json`.
- Added SB3 PPO debug training utilities under `pirl_navrl/training/`.
- Added CLI scripts:
  - `scripts/train_task05_ppo_debug.py`
  - `scripts/eval_task05_ppo_debug.py`
  - `scripts/plot_task05_training_curves.py`
- Added TASK_05 tests for curriculum, config, eval JSONL schema, and NavRL
  review documentation.
- Added `outputs/` to `.gitignore` so training artifacts are not committed.

## Local Verification

Latest local regression result:

```text
pytest -q
47 passed, 10 warnings
```

Warnings are Gymnasium `Box` float precision warnings from existing observation
spaces.

## Local Runs Performed

The following were run locally to verify the chain, with outputs kept under the
ignored `outputs/` directory or `/tmp`:

- Random / untrained eval smoke: run and JSONL schema inspected.
- PPO debug training smoke: run with a tiny temporary config, then deleted.
- Default PPO debug training: run with `configs/task05_ppo_debug_train.json`
  at `total_timesteps=10000`.
- Checkpoint eval: run for the default debug checkpoint.
- GUI eval: run for the default debug checkpoint.
- Additional 50k debug inspection: run locally to probe whether behavior
  improved within TASK_05's debug bound. It is not a baseline and is not a
  formal result.

No checkpoint, monitor CSV, eval JSONL, plot PNG, TensorBoard log, video, or
large output artifact is intended to be committed.

## Observed Behavior

The training and eval pipeline works end to end, but the current PPO debug
policy does not reliably reach the goal. Observed checkpoint evals timed out in
the simple no-obstacle level. This is a behavior observation for debugging the
training interface, not a performance conclusion.

## Current Boundary

TASK_05 remains:

- single-env debug/smoke training;
- no formal baseline;
- no multi-seed benchmark;
- no formal success rate;
- no PIRL risk/intent module training;
- no EGO-Planner baseline;
- no dynamic obstacle training.

Formal training should only be considered after adding VecEnv / VecNormalize,
separate eval envs, stronger reward/action diagnostics, and explicit
experiment-management rules.
