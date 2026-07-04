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

## Detailed Review Table

| Area | NavRL file / module / symbol | NavRL observed design | PIRL-NavRL adopted / not adopted | Adaptation reason | License / attribution note |
| --- | --- | --- | --- | --- | --- |
| Scenario generation | `external/NavRL/quick-demos/env.py`, `sample_free_start`, `sample_free_goal` | Rejection sampling chooses collision-free starts/goals inside a bounded region and keeps start sufficiently far from goal. | Adopted as a pattern in `pirl_navrl/scenarios/curriculum.py`, `sample_start_goal`. | TASK_05 needs deterministic, seed-controlled start/goal sampling before PPO can be debugged. The implementation is new and uses PIRL-NavRL dataclasses. | Reference only; no code copied. NavRL remains under `external/NavRL` with its own `LICENSE`. |
| Static obstacle generation | `external/NavRL/quick-demos/env.py`, `generate_obstacles_grid` | Grid-style circular obstacle sampling with radius range and clearance checks against existing obstacles. | Partially adopted in `sample_static_obstacles`: bounded cylinders with non-overlap and start/goal clearance. | PyBullet needs 3D cylinder/sphere bodies, not only 2D circles. TASK_05 uses smaller Crazyflie-scale obstacles. | Reference only; new implementation and schema. |
| Large static map | `external/NavRL/isaac-training/training/scripts/env.py`, `NavigationEnv._design_scene`; `external/NavRL/isaac-training/training/cfg/train.yaml` | Isaac terrain uses a large map and many heightfield obstacles; config includes `env.num_obstacles: 350`. | Not adopted for TASK_05. | TASK_05 is a gym-pybullet-drones debug smoke stage, not Isaac training or NavRL reproduction. | No Isaac/OmniDrones code imported. |
| Dynamic obstacles | `external/NavRL/isaac-training/training/scripts/env.py`, dynamic obstacle block; `external/NavRL/isaac-training/training/cfg/train.yaml`, `env_dyn` | Dynamic obstacle count, velocity range, local range, and moving obstacle state are part of the Isaac environment. | Not adopted in TASK_05. | TASK_05 explicitly keeps dynamic obstacle training for later PIRL/risk stages. | Reference only; no dynamic obstacle training claim. |
| Observation schema | `external/NavRL/quick-demos/agent.py`, `Agent.init_model`; `external/NavRL/quick-demos/ppo.py`, `PPO.__call__` | Observation includes state, lidar tensor, direction, and dynamic obstacle tensor. | Not copied. TASK_05 keeps TASK_04 flat observation from `pirl_navrl/platforms/gym_pybullet_drones/observation_adapter.py`. | Current platform does not yet expose NavRL-style lidar/dynamic obstacle tensors. Fixed flat observation is easier to validate with SB3. | No model/schema code copied. |
| Action schema | `external/NavRL/quick-demos/ppo.py`, `ActorConfig.action_limit`, `PPO.__call__`; `external/NavRL/quick-demos/utils.py`, `vec_to_world` | PPO outputs a bounded velocity-like action that is transformed relative to direction. | Adopted only at the contract level: normalized 3D desired velocity via `pirl_navrl/platforms/gym_pybullet_drones/action_adapter.py`. | Velocity action is safer for high-level Crazyflie control than direct RPM policy at this stage. | Conceptual reference only. |
| Reward design | `external/NavRL/isaac-training/training/scripts/env.py`, `_compute_reward_and_done` | Reward emphasizes goal progress, safety/clearance, action smoothness, and task termination conditions. | Partially adopted through existing TASK_04 reward terms in `pirl_navrl/evaluation/reward.py`. | Reuses local tested reward module while keeping NavRL's broad shaping categories. | No reward code copied. |
| Termination / timeout | `external/NavRL/isaac-training/training/scripts/env.py`, `_compute_reward_and_done`; `train.yaml`, `max_episode_length` | Episode length and collision/bounds conditions are explicit in the training env. | Adopted with local semantics: `terminated = success or collision`, `truncated = timeout`. | Gymnasium/SB3 needs clear task-level termination/truncation contract. | Local implementation. |
| Training config | `external/NavRL/isaac-training/training/cfg/ppo.yaml`, `train.yaml` | Config-driven PPO parameters, seed, eval interval, save interval, environment size, and logging mode. | Adopted as a small JSON debug config in `configs/task05_ppo_debug_train.json`. | TASK_05 needs reproducible small training without Hydra/Isaac dependencies. | Parameter ranges informed by NavRL; config is new. |
| Runner | `external/NavRL/isaac-training/training/scripts/train.py` | A runner builds env, policy, logging, checkpoints, and periodic evaluation. | Adopted structurally in `scripts/train_task05_ppo_debug.py` and `pirl_navrl/training/sb3_ppo_debug.py`. | Keeps a simple CLI and SB3 workflow appropriate for local debug. | New implementation. |
| Eval | `external/NavRL/isaac-training/training/scripts/eval.py`; `external/NavRL/quick-demos/simple-navigation.py` | Separate evaluation/demo paths visualize or inspect a trained policy. | Adopted structurally in `scripts/eval_task05_ppo_debug.py` and JSONL rollout export. | PIRL-NavRL needs traceable diagnostic eval and GUI playback, not formal benchmark yet. | New implementation. |
| Logging / checkpoints | `external/NavRL/isaac-training/training/cfg/train.yaml`, `wandb`, `save_interval`; `train.py` | Uses checkpointing and wandb/offline logging for training management. | Partially adopted: SB3 checkpoints and Monitor CSV under ignored `outputs/task05/...`; no wandb. | Keeps local artifacts isolated and avoids committing training outputs. | No NavRL logging code copied. |
| ROS deployment | `external/NavRL/ros1/navigation_runner/scripts/navigation.py`, `policy_server.py`; `external/NavRL/ros2/navigation_runner/scripts/navigation.py` | Deployment code wraps policy inference behind ROS navigation/perception interfaces. | Not adopted in TASK_05. | TASK_05 is pre-baseline local PyBullet debug training. ROS deployment is later-stage work. | Reference only. |

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
