# TASK_08: NavRL Actual-Code-Aligned Curriculum Training

## 0. Goal

TASK_08 now uses the actual public NavRL code as the primary reference, not only the paper or high-level description.

Primary NavRL reference:

```text
repo: https://github.com/Zhefan-Xu/NavRL
observed public commit: 3725bcc2e7c1be4ecf1455d922299ae85042603a
core file: isaac-training/training/scripts/env.py
local copy: external/NavRL, local commit must be recorded by Codex
```

TASK_08 adapts NavRL to gym-pybullet-drones / PyBullet:

```text
NavRL dict observation
NavRL 8D state
NavRL lidar scan encoding
NavRL dynamic_obstacle 10D channel
3D navigation and 3D velocity-style action
NavRL safe-navigation reward structure
smaller PyBullet-compatible forest curriculum
PIRL-NavRL latent semantic obstacle extension
```

TASK_08 is not a paper-result stage and must not claim NavRL reproduction. Do not commit checkpoints, outputs, videos, GIFs, TensorBoard, or wandb artifacts.

## 1. Scope boundaries

TASK_08 does not do:

```text
formal paper success-rate table
formal NavRL benchmark reproduction
raw RGB/RGB-D policy input
CNN vision encoder
EGO baseline
PIRL final risk module
formal safety shield
unbounded reward/PPO tuning
```

Camera is diagnostic / visualization only.

Safety shield is only an identity placeholder:

```text
policy_output -> identity_safety_filter -> action_adapter
```

Formal safety shield work starts in TASK_09.

## 2. Stage 0: source study first

Before core implementation, create or update:

```text
docs/task08_navrl_source_index.md
docs/task08_navrl_alignment_table.md
docs/TASK_08_FROM_TASK_07_FAILURE_ANALYSIS.md
```

`docs/task08_navrl_source_index.md` must record:

```text
NavRL repo URL
observed public commit
external/NavRL local commit
file path
function / class / config name
what it controls
strict reference / adapted / extension
whether code snippet migration is used
license / attribution note
```

At minimum, inspect:

```text
NavigationEnv.__init__
NavigationEnv._design_scene
NavigationEnv.move_dynamic_obstacle
NavigationEnv._set_specs
NavigationEnv._compute_state_and_obs
NavigationEnv._compute_reward_and_done
```

Task07 / Stage7 history does not block TASK_08. If history is incomplete, state that in the report and continue.

## 3. Required contracts before full training

Full training cannot start until these exist:

```text
configs/task08_navrl_style_observation.json
docs/task08_observation_contract.md
configs/task08_navrl_aligned_reward.json
docs/task08_reward_alignment_report.md
configs/task08_navrl_forest_curriculum.json
configs/task08_training_budget.json
docs/task08_promotion_block_criteria.md
```

Until then, only smoke/interface checks are allowed.

## 4. Observation: follow NavRL actual schema

NavRL actual observation schema in `env.py`:

```text
state: (8,)
lidar: (1, lidar_hbeams, lidar_vbeams)
direction: (1, 3)
dynamic_obstacle: (1, dyn_obs_num, 10)
```

TASK_08 schema:

```text
state: NavRL-style 8D
direction: NavRL-style 1x3
lidar: NavRL-style lidar scan, PyBullet adapted
dynamic_obstacle: NavRL-style 1xKx10
latent_obstacle: PIRL-NavRL extension
```

First implementation:

```text
dict observation for documentation, validation, diagnostics
flattened observation for SB3 MlpPolicy
```

Do not start with MultiInputPolicy unless all shapes and feature branches are documented.

## 5. State: strict NavRL 8D candidate

NavRL state is:

```text
rpos_clipped_g: 3
  unit direction from drone to goal, expressed in goal frame

distance_2d: 1
  horizontal distance to goal

distance_z: 1
  vertical distance to goal

vel_g: 3
  drone velocity expressed in goal frame
```

Total:

```text
state_dim = 8
```

TASK_08 should follow this unless PyBullet diagnostics require adaptation. Extra fields, such as previous action, must be documented as PIRL-NavRL extensions.

## 6. Direction field

NavRL keeps a `(1, 3)` target-direction reference with z set to zero for the goal-frame transform.

TASK_08 should keep the same idea:

```text
direction shape: (1, 3)
meaning: goal-frame / target-direction reference
```

If PyBullet uses an equivalent frame transform, document the formula.

## 7. Lidar / raycast: follow NavRL encoding

NavRL uses an Isaac RayCaster with a Bpearl pattern:

```text
horizontal_res = lidar_hres
lidar_hbeams = int(360 / lidar_hres)
vertical_ray_angles = linspace(lidar_vfov_min, lidar_vfov_max, lidar_vbeams)
attach_yaw_only = True
```

NavRL lidar scan is range-minus-distance:

```text
hit_distance = norm(ray_hit_world - lidar_position_world)
clipped_hit_distance = min(hit_distance, lidar_range)
lidar_scan = lidar_range - clipped_hit_distance
```

Meaning:

```text
near obstacle -> larger lidar_scan
far/no hit -> smaller lidar_scan, near 0
```

TASK_08 primary lidar contract:

```text
use NavRL-style range-minus-distance encoding
optionally normalize by lidar_range
static obstacles are represented in lidar
NaN/inf values are invalid
```

PyBullet implementation:

```text
preferred runtime: PyBullet rayTestBatch
preferred tests: deterministic scenario-geometry raycast
```

Fallback layout if NavRL local config cannot be recovered or is too expensive:

```text
horizontal rays: 72
FOV: 360 degrees
vertical beams: 1 initially, more if feasible
max range: 5m initial PyBullet-scale candidate
encoding: NavRL range-minus-distance, normalized to [0, 1]
```

Any fallback must be documented in the alignment table.

## 8. Dynamic obstacles: separate NavRL 10D channel

NavRL uses a separate `dynamic_obstacle` observation channel.

Selection rule:

```text
select K closest dynamic obstacles by 2D distance
mask obstacles outside lidar_range
masked features are zero
```

NavRL per-obstacle feature is 10D:

```text
normalized relative position in goal frame: 3
2D distance: 1
z distance: 1
obstacle velocity in goal frame: 3
width category: 1
height category / 2D-vs-3D cue: 1
```

TASK_08 should implement:

```text
dynamic_obstacle shape: (1, K, 10)
sorting: nearest by 2D distance
range mask: lidar_range
padding: zero
coordinate frame: NavRL-style goal frame or documented equivalent
```

Default rule:

```text
dynamic obstacles stay in dynamic_obstacle channel
not duplicated into lidar unless later NavRL source review requires it
```

## 9. Latent semantic obstacle extension

Latent semantic obstacle is a PIRL-NavRL extension, not a NavRL core module.

Principle:

```text
Policy may observe current semantic risk prior.
Policy may not observe future event labels or future trajectories.
```

Recommended first schema:

```text
latent_obstacle = NavRL dynamic_obstacle 10D base + extension dims
```

Extension dims:

```text
is_active: 1
semantic_type_one_hot: 3
valid_mask: optional 1
```

Semantic classes:

```text
static_like_latent
crossing_latent
sudden_latent
```

Allowed observation information:

```text
relative position
2D/z distance
current velocity if active, otherwise zero/masked
size category
active state
semantic risk class as current observable prior
```

Forbidden observation information:

```text
future activation time
future sampled path
future velocity while inactive if not observable
hidden trigger parameters
```

Scenario generation may use trigger radius, activation delay, speed range, and motion rule, but these generation parameters must not be exposed to the policy.

## 10. Action: 3D velocity-style in PIRL-NavRL

NavRL is a 3D navigation task. It samples 3D targets and includes z distance plus 3D velocity in state.

TASK_08 action:

```text
action_dim: 3
action meaning: normalized desired velocity [vx, vy, vz]
action range: [-1, 1]
desired_velocity = action * max_speed
adapter: desired velocity -> gym-pybullet-drones control command
```

Z behavior:

```text
z velocity enabled in first implementation
z tracking diagnosed
if unstable, fallback to 2D velocity + altitude hold is allowed and must be documented
```

Must log:

```text
raw_action
clipped_action
desired_velocity
actual_velocity
velocity_tracking_error
action_clipping_fraction
altitude_error / altitude_drift
```

If action/control tracking is unstable, fix action/control before reward tuning.

Candidate thresholds:

```text
tracking pass: mean_velocity_tracking_error <= 0.35 * max_speed
tracking warning: <= 0.60 * max_speed
tracking blocked: > 0.60 * max_speed or altitude instability
action clipping pass for promotion: <= 0.20
```

## 11. Reward: follow NavRL actual structure

NavRL reward terms:

```text
static log-clearance reward from lidar
dynamic log-clearance reward
velocity-toward-goal reward
velocity smoothness penalty
height-range penalty
collision termination
timeout truncation
```

NavRL final pattern:

```text
with dynamic obstacles:
  reward = reward_vel + 1
         + reward_safety_static * 1.0
         + reward_safety_dynamic * 1.0
         - penalty_smooth * 0.1
         - penalty_height * 8.0

without dynamic obstacles:
  reward = reward_vel + 1
         + reward_safety_static * 1.0
         - penalty_smooth * 0.1
         - penalty_height * 8.0
```

TASK_08 starts from:

```text
reward = velocity_toward_goal
       + alive_or_base_reward
       + static_log_clearance_reward
       + dynamic_log_clearance_reward
       - velocity_smoothness_penalty
       - height_range_penalty
       - latent_semantic_risk_penalty
```

Collision:

```text
primary: collision terminates episode
explicit collision penalty: optional PyBullet adaptation, not default
```

Latent risk:

```text
PIRL-NavRL extension
logged separately
initially lower than collision/static risk because it is semantic prior
```

## 12. Reward coefficients and one-time scaling

Initial coefficient priority:

```text
use NavRL actual coefficients when applicable:
  static safety: 1.0
  dynamic safety: 1.0
  smoothness: 0.1
  height: 8.0
  base reward: +1

rescale only if PyBullet units make term magnitudes clearly wrong
justify latent risk coefficient from diagnostics
```

One-time scaling rule:

```text
NavRL candidate coefficients
-> PyBullet scale normalization
-> easy curriculum diagnostics
-> one evidence-based scaling adjustment per reward profile / curriculum family
-> freeze or blocked
```

Bug fixes do not count as reward tuning.

Before reward scaling, these diagnostics must exist:

```text
reward_terms_stats.json
distance_curve.json
action_control_tracking.json
obs_stats.json
lidar_stats.json
dynamic_obstacle_stats.json
latent_obstacle_stats.json
```

## 13. Forest curriculum and training budget

Keep the NavRL forest idea, but adapt scale to PyBullet.

Levels:

```text
static_forest_easy / medium / hard
dynamic_forest_easy / medium / hard
latent_semantic_forest_easy / medium / hard
mixed_forest_target
```

Training route:

```text
static_forest_easy
-> dynamic_forest_easy
-> latent_semantic_forest_easy
-> medium levels
-> hard levels if promoted
-> mixed_forest_target stress test only after earlier promotion
```

`configs/task08_navrl_forest_curriculum.json` must include numeric values:

```text
arena size
static obstacle count / density / radius range
dynamic obstacle count / speed range
latent obstacle count / semantic distribution / trigger/risk radius
goal distance range
height range
episode horizon
lidar_range
fixed train seeds
fixed eval seeds
```

Candidate budget:

```text
smoke_steps: 4096
debug_train_steps: 50000
easy_full_train_steps: 300000
medium_full_train_steps: 500000
hard_full_train_steps: optional 1000000
num_envs: 4
num_train_seeds: 3
eval_episodes_per_level: 16
```

## 14. Scripts

新增或更新：

```text
configs/task08_training_budget.json
scripts/train_task08_navrl_aligned_curriculum.py
scripts/eval_task08_navrl_aligned_policy.py
scripts/render_task08_topdown_cases.py
```

Required modes:

```text
--mode smoke
--mode train
--mode eval
--mode blocked
--curriculum-level static_forest_easy|dynamic_forest_easy|latent_semantic_forest_easy|...
```

## 15. Evaluation and promotion

Each key level evaluates:

```text
random policy
heuristic policy
trained PPO policy
```

Promotion thresholds:

```text
trained mean final_distance improves over random by >= 10%
trained collision rate <= random collision rate + 10 percentage points
trained timeout rate <= random timeout rate + 10 percentage points
action_clipping_fraction <= 0.20
obs/lidar/dynamic/latent stats finite and non-degenerate
velocity_toward_goal reward positive or improving on easy levels
static/dynamic clearance distribution not collapsed into near-collision
```

If heuristic fails, check scene / observation / lidar / action-control before PPO.

If heuristic succeeds but trained fails, check reward scale / PPO / flattening / observation normalization.

Do not enter harder levels without promotion or a specific documented exception.

## 16. Diagnostics and reports

Ignored outputs must include:

```text
obs_stats.json
lidar_stats.json
dynamic_obstacle_stats.json
latent_obstacle_stats.json
reward_terms_stats.json
action_control_tracking.json
distance_curve.json
training_completion_status.json
eval_summary_random_heuristic_trained.json
```

Reports:

```text
docs/TASK_08_TRAINING_PROTOCOL_REPORT.md
docs/TASK_08_COMPLETION_REPORT.md
```

If incomplete:

```text
docs/TASK_08_BLOCKED_REPORT.md
```

Reports must include:

```text
NavRL public repo and commit
external/NavRL local commit
NavRL files/functions studied
actual NavRL observation schema
actual NavRL lidar encoding
actual NavRL dynamic_obstacle 10D schema
PIRL-NavRL latent extension
PyBullet adaptations
reward alignment and coefficients
one-time reward scaling decision
curriculum numeric levels
fixed eval seeds
random / heuristic / trained comparison
action/control tracking diagnostics
top-down replay or fallback summary
whether TASK_09 can start
```

## 17. Completion criteria

TASK_08 is complete only if:

1. `pytest -q` passes.
2. NavRL source index is complete.
3. Alignment table is complete.
4. Task07 failure analysis exists or states history is insufficient.
5. Observation contract uses NavRL actual schema plus latent extension.
6. State follows NavRL 8D or documents adaptation.
7. Lidar uses NavRL range-minus-distance encoding or documents adaptation.
8. Dynamic obstacle uses NavRL-style `(1, K, 10)` schema or documents adaptation.
9. Latent semantic obstacle does not expose future trigger time or future path.
10. Action is 3D velocity-style or documents fallback.
11. Reward starts from NavRL actual structure.
12. Reward coefficients and one-time scaling are documented.
13. Forest curriculum has numeric config.
14. Random / heuristic / trained comparison is complete.
15. Easy static / dynamic / latent levels show learning signal, or blocked reason is specific.
16. Top-down replay or fallback summary exists.
17. No large artifacts are committed.

## 18. Completed / blocked definition

```text
completed_success:
  static_forest_easy, dynamic_forest_easy, and latent_semantic_forest_easy show learning signal;
  reports, tests, diagnostics, and replay/fallback are complete.

completed_blocked:
  engineering pipeline, contracts, diagnostics, and reports are complete;
  one or more easy levels fail;
  blocked reason is specific and evidence-based.

TASK_09 can start:
  observation/action/reward/curriculum interfaces are stable;
  identity safety filter interface exists;
  at least static + dynamic easy behavior is usable, or limitations are clearly documented.
```

## 19. Remaining implementation choices

Codex must resolve during implementation:

1. Exact local `external/NavRL` commit hash.
2. Exact NavRL lidar config values from local config files, if present.
3. PyBullet vertical lidar beam count.
4. Initial PyBullet `max_speed`, `lidar_range`, arena size, and height range.
5. Latent obstacle extension dimensionality after NavRL 10D base.
6. Whether explicit collision penalty is needed in PyBullet, or termination-only is enough.
