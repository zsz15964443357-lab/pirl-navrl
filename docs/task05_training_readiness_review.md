# TASK_05 Training Readiness Review

This review checks whether the TASK_03/TASK_04 stack is ready for a small
debug PPO training run.

## Ready Items

- `Task04GymPybulletDronesRLEnv` is a Gymnasium env with fixed observation and
  action spaces.
- Observation is a finite flat vector of size 19.
- Action is normalized `Box([-1, 1], shape=(3,))`.
- Action is interpreted as desired velocity through the TASK_04 velocity
  adapter, not direct RPM control.
- Reward is finite and decomposed into named terms.
- Task-level termination is `terminated = success or collision`.
- Task-level truncation is `truncated = timeout`.
- `platform_terminated` and `platform_truncated` are retained in `info`.
- Collision, success, and timeout are exposed in `info` and JSONL.
- Custom obstacles are created as PyBullet collision bodies.
- JSONL rollout records include metadata, initial state, step records, and
  summary records.
- GUI and trace replay can display start, goal, obstacles, trajectory, action
  direction, and terminal status.

## Fixes and Additions for TASK_05

- Added a seed-controlled curriculum generator with three levels.
- Added a training wrapper that regenerates the curriculum scenario on reset.
- Added SB3 PPO debug training script and config.
- Added checkpoint/log output under ignored `outputs/task05/...`.
- Added eval rollout script for random/untrained policy and saved checkpoints.
- Added optional training curve plotting from SB3 Monitor CSV logs.

## Current Limits

- TASK_05 is not a baseline.
- TASK_05 does not train PIRL risk or intent modules.
- TASK_05 does not connect EGO-Planner.
- TASK_05 does not run dynamic obstacle training.
- TASK_05 does not report formal success rate, multi-seed statistics, or paper
  metrics.
- The first PPO config is intentionally small and only verifies the training
  path.

## Training Boundary

All generated training artifacts must stay under `outputs/`, which is ignored
by git. Do not commit checkpoints, TensorBoard logs, monitor files, videos,
wandb runs, or evaluation JSONL outputs.
