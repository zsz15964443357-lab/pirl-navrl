# NavRL Code Review for TASK_05

TASK_05 uses NavRL as an engineering reference only. This is not a NavRL
baseline, not a reproduction, and does not use NavRL checkpoints or results.

## Repository Structure

The local reference checkout is under `external/NavRL`.

- `quick-demos/`: lightweight 2D navigation demos, obstacle sampling helpers,
  policy loading, and simple visualization code.
- `isaac-training/training/`: the full Isaac/OmniDrones training environment,
  PPO implementation, config files, evaluation script, and logging/checkpoint
  flow.
- `ros1/` and `ros2/`: deployment-side navigation and simulator integration.
- `media/` and vendored third-party code: reference material only, not imported
  into PIRL-NavRL.

## Scenario, Obstacle, and Start/Goal Design

The quick demos use bounded random regions, grid-style static obstacle sampling,
and rejection sampling for start/goal positions so the robot does not begin in
collision and the goal is not inside an obstacle. The Isaac training stack uses
a larger terrain map with many static obstacles and a separate dynamic obstacle
configuration.

Relevant reference patterns:

- fixed map/range per experiment;
- seed-controlled randomization;
- start/goal rejection sampling;
- obstacle clearance checks;
- increasing difficulty through obstacle count, travel distance, and episode
  length.

TASK_05 adopts the same pattern at a smaller PyBullet scale:

- arena `x/y: [-5, 5]`, `z: [0.3, 3.0]`;
- three curriculum levels;
- deterministic seed-controlled start, goal, and static obstacle generation;
- no dynamic obstacle training in TASK_05.

## Observation, Action, and Reward Design

NavRL training combines robot state, goal direction, lidar-like static obstacle
features, and dynamic obstacle features. Its action is a 3D velocity-like
command, bounded by an action limit, then transformed into world-frame motion.
Its reward emphasizes goal progress, safety/clearance, and smooth behavior.

TASK_05 does not copy NavRL's network or lidar stack. It keeps the TASK_04
Gymnasium observation:

- position;
- velocity;
- goal and relative goal;
- distance to goal;
- nearest obstacle relative position;
- nearest obstacle distance and clearance;
- step fraction.

The action remains `Box([-1, 1], shape=(3,))`, interpreted as normalized desired
velocity and scaled by `max_speed`. Reward remains the TASK_04 diagnostic reward:
progress, distance penalty, action penalty, clearance penalty, collision penalty,
success bonus, and timeout penalty.

## Training, Runner, Logging, and Checkpoint Design

NavRL's training stack uses explicit config files, runner scripts, periodic
evaluation, checkpointing, and wandb/offline logging. TASK_05 adopts only the
lightweight structure:

- JSON config under `configs/`;
- script entry points under `scripts/`;
- checkpoints and logs under `outputs/task05/...`;
- optional monitor curve plotting;
- JSONL diagnostic eval rollouts.

TASK_05 uses Stable-Baselines3 PPO instead of NavRL's TorchRL/Isaac PPO stack.

## Adopted Designs

- Seed-controlled randomized scenarios.
- Curriculum levels that change travel distance and obstacle count.
- Velocity-style action contract rather than direct motor/RPM control.
- Config-driven training and evaluation scripts.
- Output isolation under an ignored directory.

## Designs Not Adopted Yet

- Isaac Sim / OmniDrones training.
- NavRL lidar tensor schema.
- NavRL dynamic obstacle training.
- NavRL PPO implementation, checkpoint format, and pretrained models.
- ROS deployment stack.
- Multi-seed benchmark or formal baseline comparison.

## Attribution and License Notes

NavRL is kept as an external reference repository with its own license files.
TASK_05 references high-level design patterns and parameter scale only. The new
PIRL-NavRL code uses this repository's own dataclasses, Gymnasium wrapper, SB3
integration, and JSONL recorder.

## TASK_05 NavRL-Informed Choices

TASK_05 implements:

- `pirl_navrl/scenarios/curriculum.py`;
- `configs/task05_curriculum_levels.json`;
- SB3 PPO debug training through `pirl_navrl/training/sb3_ppo_debug.py`;
- diagnostic evaluation through `pirl_navrl/training/eval.py`;
- CLI scripts for train, eval, and plotting.

This is a training-chain smoke stage. It is not a paper result.
