# TASK_08：NavRL-Aligned Curriculum Training and Latent Semantic Dynamic Obstacles

## 1. 阶段定位

TASK_08 是在 TASK_07 没有得到稳定好效果之后，对训练路线做一次更清晰的重构：不再把项目当作从零设计 PPO 避障系统，而是尽量严格迁移 NavRL 的训练体系到 gym-pybullet-drones / PyBullet，并加入本项目的扩展点：latent semantic dynamic obstacles。

TASK_08 的目标不是继续盲目调 reward，也不是只靠增加训练步数碰运气，而是建立一套 NavRL-aligned 的训练闭环：

```text
NavRL-style observation
+ NavRL-style action semantics
+ NavRL-style reward structure
+ NavRL-style forest curriculum
+ PyBullet-compatible scaling
+ latent semantic dynamic obstacle extension
```

TASK_08 可以进入真正课程训练，但必须建立在明确的 NavRL 对齐表、场景尺度适配、observation 适配和训练诊断基础上。

## 2. 和 NavRL 的关系

本项目和 NavRL 的核心差异应被限定为：

```text
simulation backend: Isaac Sim -> gym-pybullet-drones / PyBullet
scene scale: large NavRL forest -> smaller PyBullet-compatible forest
new research extension: latent semantic dynamic obstacles
training budget: large parallel training -> smaller curriculum training
```

除以上差异外，能严格参考 NavRL 的地方应尽量严格参考，包括：

```text
state representation structure
action semantics
reward term structure
forest randomization and curriculum
static obstacle raycast representation
dynamic obstacle state representation
PPO-based training loop
safety-shield direction for later stages
```

## 3. 必须新增 NavRL 对齐表

新增：

```text
docs/task08_navrl_alignment_table.md
```

表格至少包含：

```text
Module
NavRL design
Strictly referenced? yes / adapted / no
PIRL-NavRL implementation
Difference from NavRL
Reason for difference
Validation evidence
Status: candidate / validated / frozen
```

必须覆盖以下模块：

```text
observation/state representation
static obstacle raycast / lidar-like representation
dynamic obstacle representation
action representation
reward structure
forest curriculum
PPO training setup
safety shield placeholder
latent semantic dynamic obstacle extension
```

不得只写“参考 NavRL”。必须明确哪些地方严格参考，哪些地方因为 PyBullet 或 latent semantic extension 做了适配。

## 4. Observation：严格对齐 NavRL-style structure

TASK_08 必须把主线 observation 从当前 nearest-obstacle flat features 升级为 NavRL-style dict observation：

```text
{
  "state": ...,
  "direction": ...,
  "lidar": ...,
  "dynamic_obstacle": ...,
  "latent_obstacle": ...   # PIRL-NavRL extension, optional or merged into dynamic_obstacle
}
```

建议新增：

```text
pirl_navrl/observation/navrl_style_observation.py
configs/task08_navrl_style_observation.json
```

### 4.1 state

严格参考 NavRL 的思想：policy 不直接吃原始 camera 图像，而是吃结构化低维状态。

`state` 至少应包含：

```text
current velocity or normalized velocity
height or z error if relevant
previous action if available
basic motion state needed by PPO
```

### 4.2 direction

`direction` 表示目标方向和距离信息，至少包含：

```text
normalized direction to goal
distance to goal or clipped distance-to-goal
```

### 4.3 lidar / raycast

`lidar` 表示静态障碍或占据空间的 raycast / distance scan。TASK_08 当前可使用 PyBullet raycast 或 scenario geometry raycast，不要求真实 camera/depth perception。

必须配置：

```text
num_rays
field_of_view or angular distribution
max_range
height plane or 3D ray policy
normalization rule
missing-hit value
```

注意：结构严格参考 NavRL，但 ray 数量、最大距离和归一化必须按 PyBullet 场景尺度定标，不能盲目照搬。

### 4.4 dynamic_obstacle

`dynamic_obstacle` 表示最近 K 个动态障碍的结构化状态。至少包含：

```text
relative position
relative velocity
distance
radius or safety size
valid mask
```

必须配置：

```text
max_dynamic_obstacles_k
sorting rule: nearest / time-to-collision / risk score
normalization rule
padding rule
```

### 4.5 latent_obstacle

这是本项目相对 NavRL 的核心扩展。可以单独作为 `latent_obstacle`，也可以并入 `dynamic_obstacle`，但必须明确。

不得直接泄露未来 trigger label。允许提供：

```text
relative position
current velocity if active
is_active
semantic type or risk class
trigger distance proxy if observable by scenario semantics
distance-to-risk-region if not future-leaking
valid mask
```

如果使用 semantic type，必须记录它是否为 policy 可观测语义，而不是未来信息泄露。

## 5. Action：严格参考 NavRL velocity-style action semantics

TASK_08 主线 action 应保持 velocity-style action，不回到手工 waypoint planner。

要求：

```text
policy outputs normalized desired velocity or velocity command
action is clipped by max_speed
action/control tracking diagnostics are recorded
altitude behavior is explicit and documented
```

必须输出诊断：

```text
raw_action
clipped_action
desired_velocity
actual_velocity
tracking_error
action_clipping_fraction
```

## 6. Reward：严格参考 NavRL structure，数值按 PyBullet 定标

Reward 结构应严格参考 NavRL-style safe navigation reward，而不是自由发明。

建议结构：

```text
reward = progress
       + goal_success
       - collision_penalty
       - clearance_or_static_risk_penalty
       - dynamic_obstacle_risk_penalty
       - action_or_smoothness_penalty
       - timeout_penalty
       - latent_semantic_risk_penalty   # PIRL-NavRL extension
```

必须新增或更新：

```text
configs/task08_navrl_aligned_reward.json
docs/task08_reward_alignment_report.md
```

要求：

```text
NavRL reward term -> PIRL-NavRL reward term mapping
initial coefficient source or rationale
reward term statistics before/after tuning
reason for every coefficient change
final candidate / validated / frozen status
```

Reward 系数不能无限调。TASK_08 允许一次 NavRL-aligned scaling adaptation：

```text
NavRL-style candidate weights
-> PyBullet scale normalization
-> easy curriculum diagnostics
-> one-time adjustment if evidence requires
-> freeze or mark blocked
```

## 7. Forest curriculum：严格参考 NavRL random forest 思路

TASK_08 不再优先做手工小场景，而是使用随机森林课程训练。

默认课程：

```text
static_forest_easy
static_forest_medium
static_forest_hard

dynamic_forest_easy
dynamic_forest_medium
dynamic_forest_hard

latent_semantic_forest_easy
latent_semantic_forest_medium
latent_semantic_forest_hard

mixed_forest_target
```

课程参数包括：

```text
arena size
static obstacle count
static obstacle density
obstacle radius range
dynamic obstacle count
dynamic obstacle speed range
latent obstacle count
latent trigger radius or risk radius
semantic class distribution
goal distance
episode horizon
```

## 8. NavRL-style high-density target，不直接从 target 起训

NavRL 可以在更大并行规模和成熟训练栈下使用高密度森林。TASK_08 应定义 NavRL-style target levels，但训练应从 PyBullet-compatible easy / medium 开始。

正确路线：

```text
small/easy forest for learning signal validation
-> medium forest for curriculum growth
-> hard forest for robustness
-> target forest for NavRL-style density stress test
```

不得用降低 eval 难度制造成功。eval seeds 和 level 配置必须固定记录。

## 9. Training protocol

新增：

```text
configs/task08_training_budget.json
scripts/train_task08_navrl_aligned_curriculum.py
scripts/eval_task08_navrl_aligned_policy.py
scripts/render_task08_topdown_cases.py
```

训练模式：

```text
--mode smoke
--mode train
--mode eval
--mode blocked
--curriculum-level static_forest_easy|...|mixed_forest_target
```

要求：

```text
smoke only checks dependencies and interfaces
train writes training_completion_status.json
eval uses fixed seeds and fixed level configs
blocked writes docs/TASK_08_BLOCKED_REPORT.md
no checkpoints, outputs, videos, tensorboard, wandb committed
```

## 10. Random / heuristic / trained evaluation

每个关键 level 至少评估：

```text
random policy
heuristic policy
trained PPO policy
```

最小判断：

```text
heuristic should beat random on easy and medium levels
trained should beat random after training
trained should approach heuristic on easy levels
if heuristic fails, suspect scene/observation/action/control
if heuristic succeeds but trained fails, suspect reward/PPO/observation scaling
```

Heuristic 不是论文 baseline，只是 sanity check。

## 11. 训练成功不只看步数

TASK_08 明确禁止“只要训练步数足够多就会好”的假设。增加步数只有在以下条件满足时才有意义：

```text
scene distribution is learnable
observation contains useful information
reward terms provide correct gradients
action/control tracking is stable
curriculum level is not too hard at start
training diagnostics are not collapsed
```

如果高密度 target 失败，优先调整 curriculum step size、obstacle count、density、speed、horizon，而不是立即改 reward/PPO。

## 12. Reports

新增：

```text
docs/TASK_08_TRAINING_PROTOCOL_REPORT.md
docs/TASK_08_COMPLETION_REPORT.md
```

如果未完成：

```text
docs/TASK_08_BLOCKED_REPORT.md
```

报告必须说明：

```text
how Task08 aligns with NavRL
what is strictly referenced from NavRL
what is adapted because of PyBullet scale
how latent semantic obstacles extend NavRL
observation schema and stats
reward alignment and final weights
curriculum levels and fixed eval seeds
random / heuristic / trained comparison
training curves and diagnostics
top-down replay cases
whether Task09 can start
```

## 13. 验收标准

TASK_08 完成时必须满足：

1. `pytest -q` 通过；
2. `docs/task08_navrl_alignment_table.md` 完成；
3. 主线 observation 使用 NavRL-style dict observation：`state / direction / lidar / dynamic_obstacle`，并明确 latent extension；
4. lidar/raycast observation 有配置、归一化、统计诊断；
5. dynamic_obstacle features 有 K、排序、padding、mask、归一化；
6. latent semantic dynamic obstacle features 不泄露未来 trigger label；
7. action 仍为 velocity-style，并有 tracking diagnostics；
8. reward structure 对齐 NavRL-style safe navigation reward，并记录系数来源和调整证据；
9. forest curriculum 包含 static / dynamic / latent semantic / mixed target；
10. 不直接从 target forest 起训；
11. fixed eval seeds 和 fixed level configs 已记录；
12. random / heuristic / trained 对比完成；
13. 至少 easy static / dynamic / latent semantic levels 显示 learning signal；
14. 训练结果有 top-down replay 或 fallback summary；
15. 如果没有达到预期效果，必须写 blocked report，而不是继续盲调；
16. 不提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 14. 明确不做

TASK_08 不做：

```text
formal paper success-rate table
full sim-to-real experiment
real RGB-D perception stack
EGO baseline
PIRL final risk module
NavRL reproduction claim
```

TASK_08 完成后，如果 NavRL-aligned curriculum 能稳定学习，下一阶段可以进入：

```text
TASK_09: NavRL-style safety shield adaptation
TASK_10: latent semantic risk / PIRL module
TASK_11: formal evaluation protocol
```
