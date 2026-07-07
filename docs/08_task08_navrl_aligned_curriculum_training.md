# TASK_08: NavRL Code-Aligned Curriculum Training and Latent Semantic Dynamic Obstacles

## 1. 阶段定位

TASK_08 是一次训练路线重构：不再把项目当作从零设计 PPO 避障系统，而是以 `external/NavRL` 为主要参考对象，做 NavRL-style 训练闭环迁移。

目标是先建立清楚的代码级对齐、observation / lidar / action / reward / curriculum contract，再做从 easy forest 开始的 staged curriculum training。

TASK_08 不追求论文结果，不声称复现 NavRL，不提交 checkpoints / outputs / videos / TensorBoard / wandb。

主线流程：

```text
read external/NavRL source
-> write source index and alignment table
-> define contracts
-> implement NavRL-style observation + velocity action + safe-navigation reward
-> train from easy forest curriculum
-> evaluate random / heuristic / trained
-> freeze, promote, or write blocked report
```

本项目已经允许：

```text
- external/ 下已有 NavRL 本地 clone
- 允许结构参考 NavRL
- 允许在遵守 license / attribution 的前提下迁移小段代码片段
```

核心差异限定为：

```text
simulation backend: NavRL backend -> gym-pybullet-drones / PyBullet
scene scale: NavRL forest scale -> smaller PyBullet-compatible forest
research extension: latent semantic dynamic obstacles
training budget: large training -> smaller staged curriculum training
```

## 2. 边界

TASK_08 不做：

```text
formal paper success-rate table
formal NavRL benchmark reproduction
full sim-to-real experiment
real RGB-D policy input
CNN vision encoder
EGO baseline
PIRL final risk module
formal safety shield
unbounded reward/PPO tuning
```

Camera 只能用于 diagnostic / visualization，不进入 policy input。

Safety shield 只保留 identity interface：

```text
policy_output -> identity_safety_filter -> action_adapter
```

正式 safety shield adaptation 放到 TASK_09。

## 3. Stage 0: 先读 NavRL 代码

核心训练代码前必须先完成：

```text
docs/task08_navrl_source_index.md
docs/task08_navrl_alignment_table.md
docs/TASK_08_FROM_TASK_07_FAILURE_ANALYSIS.md
```

Task07 / Stage7 历史资料不作为 TASK_08 启动阻塞。如果 Task07 completion / blocked report 不完整，可以在 TASK_08 report 中说明历史信息不足，不因此停工。

### 3.1 NavRL source index

`docs/task08_navrl_source_index.md` 必须列出实际读过的 NavRL 文件：

```text
NavRL repository URL or local path
commit / branch / version if available
file path
function / class / config name
what it controls
whether we strictly follow it
whether we adapt it
whether we migrate a code snippet
license / attribution note
```

如果某个模块找不到对应 NavRL 源码，写 `not found`，不要凭论文或记忆假装代码对齐。

### 3.2 Alignment table

`docs/task08_navrl_alignment_table.md` 必须覆盖：

```text
observation/state representation
static obstacle raycast / lidar-like representation
dynamic obstacle representation
action representation
reward structure
PPO / policy setup
forest curriculum
training script and logging pattern
safety shield placeholder
latent semantic dynamic obstacle extension
```

表格列：

```text
Module
NavRL code file / config
NavRL design from code
Reference level: strict / adapted / no / extension
PIRL-NavRL implementation
Difference from NavRL
Reason for difference
Validation evidence
Status: candidate / validated / frozen / blocked
```

## 4. 启动前 contracts

进入 full training 前，必须完成：

```text
configs/task08_navrl_style_observation.json
docs/task08_observation_contract.md
configs/task08_navrl_aligned_reward.json
docs/task08_reward_alignment_report.md
configs/task08_navrl_forest_curriculum.json
configs/task08_training_budget.json
docs/task08_promotion_block_criteria.md
```

Contracts 没完成时，只允许 smoke / interface check，不允许 full training。

## 5. Observation design

Observation 结构参考 NavRL。TASK_08 主线使用 NavRL-style dict schema：

```text
{
  "state": ...,
  "direction": ...,
  "lidar": ...,
  "dynamic_obstacle": ...,
  "latent_obstacle": ...
}
```

第一版采用：

```text
dict observation: documentation, validation, diagnostics
flattened observation: SB3 MlpPolicy training input
```

不优先上 MultiInputPolicy / custom feature extractor。只有在 NavRL 源码依据清楚、shape 也写清楚时才作为可选升级。

`docs/task08_observation_contract.md` 必须写清：

```text
field name
shape
unit
coordinate frame
normalization
clip range
padding rule
mask rule
flatten order
NavRL source reference
```

建议初版字段：

```text
state:
  - drone linear velocity, normalized
  - altitude or z error, if used
  - previous action, if NavRL uses it or tracking diagnostics need it
  - other basic motion state only if justified by NavRL or control needs

direction:
  - normalized direction to goal
  - clipped distance to goal

lidar:
  - static obstacle ray distances
  - normalized to [0, 1]
  - missing hit = 1.0

dynamic_obstacle:
  per obstacle:
    - relative position
    - relative velocity
    - distance
    - radius or safety size
    - valid mask

latent_obstacle:
  per obstacle:
    - relative position
    - current velocity if active, otherwise zero or masked
    - is_active
    - semantic type / risk class
    - distance-to-risk-region, if observable
    - radius or safety size
    - valid mask
```

## 6. Lidar / raycast design

Lidar / raycast 几何可以参考 NavRL。优先级：

```text
1. 如果 NavRL 源码有明确 ray count / angular layout，优先参考 NavRL。
2. 如果 NavRL 数值不适合 PyBullet scale，按 PyBullet 适配，并在 alignment table 说明原因。
3. 如果找不到明确设置，使用 fallback contract。
```

Fallback contract：

```text
num_rays: 72
fov: 360 degrees
ray plane: horizontal plane around current drone z, optionally clamped near nominal flight altitude
coordinate frame: ego/local frame
max_range: PyBullet-compatible value, e.g. 5m initially
normalization: min(distance, max_range) / max_range
missing hit: 1.0
included in lidar: static cylinders
not included in lidar by default: dynamic obstacles, latent obstacles
```

实现要求：

```text
- tests 可以先用 deterministic scenario-geometry raycast
- runtime 可以用 PyBullet rayTestBatch，但必须和 contract 一致
- default static obstacle geometry is cylinder
- cylinder footprint must be represented correctly in horizontal scan
- NaN / inf lidar values are forbidden
```

## 7. Latent semantic obstacle boundary

Latent semantic obstacle 是 PIRL-NavRL 扩展，不要求 NavRL 已有对应模块。

核心原则：

```text
Policy can observe current semantic risk prior.
Policy cannot observe future event labels.
```

允许进入 observation：

```text
relative position
current velocity if active
is_active
semantic type / risk class as current observable prior
distance-to-risk-region if observable
radius or safety size
valid mask
```

禁止进入 observation：

```text
future_activation_step
will_activate_in_n_steps
future sampled trajectory
future motion direction if inactive and unobservable
future speed if inactive and unobservable
hidden trigger random seed
will_collide_with_drone
```

第一版 semantic classes：

```text
static_like_latent
crossing_latent
sudden_latent
```

这些 class 表示当前可观察的语义风险先验，不表示 policy 知道未来一定发生什么。

每类必须在 curriculum config 中定义：

```text
trigger_radius_range
activation_delay_range
speed_range
motion_direction_rule
risk role
```

这些生成参数用于环境，不直接暴露给 policy。

## 8. Action and control tracking

Action 参考 NavRL-style velocity semantics。

主线：

```text
policy outputs normalized velocity command in [-1, 1]
action_adapter clips by max_speed
gym-pybullet-drones executes desired velocity
identity_safety_filter passes action unchanged in TASK_08
```

第一版建议：

```text
action_dim: 3
meaning: desired velocity x/y/z
z behavior: constrained and diagnosed
```

如果 gym-pybullet-drones z tracking 不稳定，可以降级为：

```text
action_dim: 2
meaning: desired velocity x/y
z behavior: altitude hold
```

必须记录：

```text
raw_action
clipped_action
desired_velocity
actual_velocity
velocity_tracking_error
action_clipping_fraction
altitude_error / altitude_drift
```

成功标准可以参考 NavRL 的诊断思路，但阈值必须按 gym-pybullet-drones 实测定。

Candidate thresholds：

```text
tracking pass:
  mean_velocity_tracking_error <= 0.35 * max_speed

tracking warning:
  0.35 * max_speed < mean_velocity_tracking_error <= 0.60 * max_speed

tracking blocked:
  mean_velocity_tracking_error > 0.60 * max_speed
  or altitude instability appears

action clipping pass for easy levels:
  action_clipping_fraction <= 0.30

action clipping pass for promotion:
  action_clipping_fraction <= 0.20

action clipping blocked:
  action_clipping_fraction > 0.50 and learning depends on clipped commands
```

硬规则：如果 action/control tracking 不稳定，先修 action/control，不先调 reward。

## 9. Reward design

Reward 结构参考 NavRL safe-navigation reward。系数先从 NavRL code/config 找来源，再按 PyBullet scale 适配。

主线 reward：

```text
reward = progress_reward
       + goal_success_reward
       - collision_penalty
       - static_clearance_or_lidar_risk_penalty
       - dynamic_obstacle_risk_penalty
       - action_or_smoothness_penalty
       - timeout_penalty
       - latent_semantic_risk_penalty
```

`configs/task08_navrl_aligned_reward.json` 必须记录：

```text
term name
NavRL source file / config
NavRL coefficient if available
PIRL-NavRL initial coefficient
scale adaptation reason
status: candidate / validated / frozen / blocked
```

`docs/task08_reward_alignment_report.md` 必须说明：

```text
NavRL reward term -> PIRL-NavRL reward term mapping
which terms are strictly referenced
which terms are PyBullet-adapted
which terms are PIRL-NavRL extensions
reward term statistics before/after adjustment
reason for every coefficient change
```

Coefficient source priority：

```text
1. Use exact NavRL code/config coefficient if directly applicable.
2. Use NavRL relative term magnitude and rescale to PyBullet units.
3. If NavRL coefficient is absent, derive from reward scale budget and document why.
```

Reward scale budget guideline：

```text
goal_success_reward:
  should dominate one episode of small shaping rewards

collision_penalty:
  should make direct collision shortcut unattractive

progress_reward:
  should provide dense learning signal but not overwhelm collision safety

static/dynamic risk:
  should affect path choice before collision

action/smoothness:
  should regularize, not prevent movement

latent risk:
  should start lower than collision/static risk because it is semantic prior, not guaranteed collision
```

### One-time scaling adaptation

Reward 不能无限调。

允许：

```text
NavRL candidate coefficients
-> PyBullet scale normalization
-> easy curriculum diagnostics
-> one evidence-based scaling adaptation
-> freeze or blocked
```

一次 adjustment 可以包含：

```text
progress scale
static/dynamic/latent risk scale
success/collision terminal magnitude
action/smoothness scale
```

不允许：

```text
failed once就随意改 reward
为了制造 success 降低 eval 难度
每次训练失败都继续换系数
不看 diagnostics 直接调 reward
```

不算 reward tuning 的情况：

```text
fix sign bug
fix unit normalization bug
fix collision detection bug
fix reward term missing from log
fix observation/control bug that made reward meaningless
```

调整 reward 前必须有：

```text
reward_terms_stats.json
distance_curve.json
action_control_tracking.json
obs_stats.json
lidar_stats.json
dynamic_obstacle_stats.json
latent_obstacle_stats.json
```

## 10. Forest curriculum

新增：

```text
pirl_navrl/scenarios/task08_navrl_forest_curriculum.py
configs/task08_navrl_forest_curriculum.json
```

默认 levels：

```text
static_forest_easy / medium / hard
dynamic_forest_easy / medium / hard
latent_semantic_forest_easy / medium / hard
mixed_forest_target
```

训练路线：

```text
static_forest_easy
-> dynamic_forest_easy
-> latent_semantic_forest_easy
-> medium levels
-> hard levels
-> mixed_forest_target stress test
```

`mixed_forest_target` 只作为 target / stress test，不作为第一训练入口。

Config 必须给具体数值：

```text
arena size
static obstacle count / density / radius range
dynamic obstacle count / speed range
latent obstacle count / semantic distribution / trigger or risk radius
goal distance
episode horizon
fixed train seeds
fixed eval seeds
```

## 11. Training scripts and budget

新增：

```text
configs/task08_training_budget.json
scripts/train_task08_navrl_aligned_curriculum.py
scripts/eval_task08_navrl_aligned_policy.py
scripts/render_task08_topdown_cases.py
```

脚本支持：

```text
--mode smoke
--mode train
--mode eval
--mode blocked
--curriculum-level static_forest_easy|dynamic_forest_easy|latent_semantic_forest_easy|...
```

Budget config 必须明确：

```text
smoke_steps
debug_train_steps
full_train_steps
num_envs
num_seeds
eval_episodes
checkpoint interval under ignored outputs
promotion criteria
blocked criteria
```

Candidate budget：

```text
smoke_steps: 4096
debug_train_steps: 50000
full_train_steps_easy: 300000
full_train_steps_medium: 500000
num_envs: 4
num_train_seeds: 3
eval_episodes_per_level: 8 or 16
```

这些是 candidate。实现时可根据机器资源调整，但必须记录原因。

## 12. Evaluation and promotion/block criteria

每个关键 level 至少评估：

```text
random policy
heuristic policy
trained PPO policy
```

Heuristic 不是论文 baseline，只是 sanity check。

推荐判断：

```text
heuristic beats random:
  scene/action/observation likely feasible

trained beats random:
  learning signal exists

trained approaches heuristic on easy:
  training stack is usable

heuristic fails:
  suspect scene/action/observation/control

heuristic succeeds but trained fails:
  suspect reward/PPO/observation scaling
```

Promotion candidate thresholds：

```text
mean final_distance improvement over random >= 10%
trained collision rate <= random collision rate + 10 percentage points
trained timeout rate <= random timeout rate + 10 percentage points
reward curve not collapsed
action_clipping_fraction <= promotion threshold
obs/lidar/dynamic/latent stats finite and non-degenerate
```

如果不满足，不能进入更难 level。必须修对应模块或写 blocked reason。

## 13. Diagnostics and outputs

训练和 eval 必须写到 ignored `outputs/`：

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

不要提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 14. Top-down replay

必须生成 PyBullet top-down replay 或 fallback summary。

Replay 至少展示：

```text
drone trajectory
start / goal
static obstacle footprints
dynamic obstacle paths
latent semantic obstacle activation / active state
success / collision / timeout / failure type
```

推荐第一版：

```text
primary: matplotlib or PyBullet top-down GIF/PNG generated from JSONL
fallback: JSON summary + static PNG
```

## 15. Reports

新增：

```text
docs/TASK_08_TRAINING_PROTOCOL_REPORT.md
docs/TASK_08_COMPLETION_REPORT.md
```

如果未完成：

```text
docs/TASK_08_BLOCKED_REPORT.md
```

Report 必须说明：

```text
which NavRL code files/configs were studied
what is strictly aligned with NavRL
what is adapted for PyBullet scale
what is PIRL-NavRL latent semantic extension
observation schema and stats
lidar geometry
reward alignment and final weights
curriculum numeric levels and fixed eval seeds
random / heuristic / trained comparison
action/control tracking diagnostics
training curves and diagnostics
top-down replay or fallback summary
whether TASK_09 can start
```

## 16. Completion criteria

TASK_08 完成时必须满足：

1. `pytest -q` 通过。
2. `docs/task08_navrl_source_index.md` 完成。
3. `docs/task08_navrl_alignment_table.md` 完成。
4. `docs/TASK_08_FROM_TASK_07_FAILURE_ANALYSIS.md` 完成；如果 Task07 信息不足，要说明不足。
5. `docs/task08_observation_contract.md` 完成。
6. 主线 observation 使用 NavRL-style dict schema，并有 fixed flatten order。
7. lidar/raycast 有具体 geometry、normalization 和统计诊断。
8. dynamic_obstacle features 有 K、排序、padding、mask、归一化。
9. latent semantic obstacle 不泄露未来 trigger / trajectory / activation time。
10. semantic classes 定义清楚。
11. action 是 velocity-style，并有 tracking diagnostics。
12. reward structure 对齐 NavRL code-style safe-navigation reward。
13. reward 系数来源、PyBullet scale adaptation 和 one-time adjustment 记录清楚。
14. forest curriculum 有 numeric config。
15. 不直接从 `mixed_forest_target` 起训。
16. fixed eval seeds 和 fixed level configs 已记录。
17. random / heuristic / trained 对比完成。
18. 至少 easy static / dynamic / latent semantic levels 显示 learning signal，或写清 blocked reason。
19. 有 top-down replay 或 fallback summary。
20. 没有达到预期效果时写 blocked report，不继续盲调。
21. 不提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 17. Completed / blocked definition

```text
completed_success:
  static_forest_easy, dynamic_forest_easy, latent_semantic_forest_easy all show learning signal;
  reports, tests, diagnostics, and replay/fallback are complete.

completed_blocked:
  engineering pipeline, contracts, diagnostics, and reports are complete;
  one or more easy levels fail;
  blocked reason is specific and evidence-based.

TASK_09 can start:
  observation/action/reward/curriculum interfaces are stable;
  safety filter placeholder interface exists;
  at least static + dynamic easy behavior is usable, or limitations are clearly documented.
```

## 18. 开工前待确认的问题

请确认这些点，确认后再进入实现：

1. `external/NavRL` 是否固定到当前本地 commit？是否需要把 commit hash 写入 source index？
2. 第一版 action 用 3D velocity，还是 2D velocity + altitude hold？
3. Lidar fallback 是否接受 `72 rays / 360 degrees / max_range 5m`？
4. Dynamic obstacles 是否保持不进入 lidar，只进入 `dynamic_obstacle` channel？
5. Latent semantic type 是否允许作为“当前可观察风险先验”进入 observation？
6. Reward 的 one-time scaling adaptation 是否按“每个 reward profile / curriculum family 一次”理解？
7. Candidate training budget 是否接受：smoke 4096、debug 50k、easy full 300k、medium full 500k、4 envs、3 train seeds？
8. Promotion threshold 是否接受：final distance 至少比 random 好 10%，collision/timeout 不比 random 多 10 个百分点以上？
