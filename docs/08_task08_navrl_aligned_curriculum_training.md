# TASK_08：NavRL Code-Aligned Curriculum Training and Latent Semantic Dynamic Obstacles

## 1. 阶段定位

TASK_08 是在 TASK_07 没有得到稳定好效果之后，对训练路线做一次更清晰的重构。TASK_08 不再把项目当作从零设计 PPO 避障系统，而是以 NavRL 训练无人机项目为主参考对象，进行代码级对齐，并迁移到 gym-pybullet-drones / PyBullet。

TASK_08 的目标不是继续盲目调 reward，也不是只靠增加训练步数碰运气，而是建立一套 NavRL-aligned 的训练闭环：

```text
NavRL code-level source study
+ NavRL-style observation
+ NavRL-style velocity action semantics
+ NavRL-style reward structure
+ NavRL-style PPO / policy setup
+ NavRL-style forest curriculum
+ PyBullet-compatible scaling
+ latent semantic dynamic obstacle extension
```

TASK_08 可以进入真正课程训练，但必须先完成 NavRL 代码级对齐表、场景尺度适配、observation contract、reward contract 和训练诊断协议。

## 2. 和 NavRL 的关系

本项目和 NavRL 的核心差异限定为：

```text
simulation backend: Isaac Sim -> gym-pybullet-drones / PyBullet
scene scale: large NavRL forest -> smaller PyBullet-compatible forest
new research extension: latent semantic dynamic obstacles
training budget: large parallel training -> smaller curriculum training
```

除以上差异外，能严格参考 NavRL 训练无人机项目代码的地方，应优先严格参考代码，而不是只参考论文描述。

必须优先严格参考：

```text
state / observation representation structure
static obstacle raycast / lidar-like representation
dynamic obstacle state representation
velocity-style action semantics
reward term structure and relative role
PPO / policy network setup
forest randomization and curriculum design
training script organization and logging pattern
safety-shield interface direction for later stages
```

注意：严格参考不等于无条件复制粘贴。必须遵守 NavRL 代码许可证和 attribution；如果直接复用小段实现或配置，必须记录来源、差异和许可边界。

## 3. Stage 0：先读 NavRL 代码，再实现

TASK_08 在写任何核心训练代码前，必须先完成 Stage 0。

新增：

```text
docs/task08_navrl_source_index.md
docs/task08_navrl_alignment_table.md
docs/TASK_08_FROM_TASK_07_FAILURE_ANALYSIS.md
```

### 3.1 NavRL source index

`docs/task08_navrl_source_index.md` 必须列出实际阅读过的 NavRL 训练项目代码来源，至少包含：

```text
NavRL repository URL or local reference path
commit / branch / version if available
file path
function / class / config name
what it controls
whether we strictly follow it
whether we adapt it
license / attribution note
```

如果找不到某个模块的 NavRL 源码，必须写明 `not found`，不能凭论文或记忆假装已经代码对齐。

### 3.2 NavRL alignment table

`docs/task08_navrl_alignment_table.md` 至少包含：

```text
Module
NavRL code file / config
NavRL design from code
Strictly referenced? yes / adapted / no
PIRL-NavRL implementation
Difference from NavRL
Reason for difference
Validation evidence
Status: candidate / validated / frozen
```

必须覆盖：

```text
observation/state representation
static obstacle raycast / lidar-like representation
dynamic obstacle representation
action representation
reward structure
PPO / policy setup
forest curriculum
training script and budget
safety shield placeholder
latent semantic dynamic obstacle extension
```

不得只写“参考 NavRL”。必须写清楚具体参考的 NavRL 文件、模块、脚本或配置。

### 3.3 Task07 failure analysis

`docs/TASK_08_FROM_TASK_07_FAILURE_ANALYSIS.md` 必须说明：

```text
Task07 attempted setup
observed failure or weak result
suspected root causes
what Task08 changes
what Task08 must not repeat
```

如果 Task07 没有正式 completion / blocked report，也必须从现有代码、日志和文档中整理 failure analysis。

## 4. 启动前 design contracts

TASK_08 不能边写代码边猜。进入训练前，必须完成以下 design contracts：

```text
configs/task08_navrl_style_observation.json
docs/task08_observation_contract.md
configs/task08_navrl_aligned_reward.json
docs/task08_reward_alignment_report.md
configs/task08_navrl_forest_curriculum.json
configs/task08_training_budget.json
docs/task08_promotion_block_criteria.md
```

这些 contracts 不完成，不能开始 full training。

## 5. Observation：严格对齐 NavRL-style structure

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
docs/task08_observation_contract.md
```

`docs/task08_observation_contract.md` 必须写明：

```text
field name
shape
unit
coordinate frame
normalization rule
clip range
padding rule
mask rule
flatten order if using MlpPolicy
NavRL source file / config reference
```

### 5.1 可以严格参考 NavRL 的部分

以下应尽量严格参考 NavRL 代码结构：

```text
state / direction / lidar / dynamic obstacle 分组方式
policy 不直接吃原始 RGB/RGB-D 图像，而吃结构化低维状态
static obstacle 通过 raycast / distance scan 表示
dynamic obstacles 通过结构化状态表示
```

### 5.2 必须适配的部分

以下不能盲目照搬，必须按 PyBullet 场景尺度定标：

```text
ray 数量
max_range
arena size
normalization range
dynamic obstacle max K
obstacle radius / safety radius
control frequency and action scale
```

### 5.3 lidar / raycast contract

Task08 第一版建议固定为：

```text
2D horizontal raycast
360-degree FOV unless NavRL code shows otherwise and can be adapted
static cylinders included in lidar
dynamic / latent obstacles represented in dynamic_obstacle / latent_obstacle channels
ray distance normalized to [0, 1]
missing hit = 1.0
```

如果 NavRL 代码使用不同 ray layout，必须在 alignment table 中说明是否严格参考或为何适配。

### 5.4 dynamic_obstacle contract

`dynamic_obstacle` 表示最近 K 个普通动态障碍，至少包含：

```text
relative position
relative velocity
distance
radius or safety size
valid mask
```

必须固定：

```text
max_dynamic_obstacles_k
sorting rule: nearest / time-to-collision / risk score
normalization rule
padding value
mask convention
```

### 5.5 latent semantic obstacle contract

这是本项目相对 NavRL 的核心扩展。可以单独输出 `latent_obstacle`，也可并入 `dynamic_obstacle`，但必须固定。

不得直接泄露未来 trigger label。允许输入：

```text
relative position
current velocity if active
is_active
semantic type or risk class
distance-to-risk-region if observable
valid mask
```

禁止输入：

```text
future_activation_step
will_activate_in_n_steps
future trajectory unavailable to a real policy
```

语义类别第一版必须固定，例如：

```text
static_like_latent
crossing_latent
sudden_latent
```

每类必须定义：

```text
trigger_radius_range
activation_delay_range
speed_range
motion_direction_rule
risk_weight or risk role
```

## 6. Policy architecture decision

Task08 必须明确 policy 输入方式。

推荐第一版：

```text
NavRL-style dict schema for documentation and validation
flattened vector for SB3 PPO MlpPolicy first implementation
```

如果使用 MultiInputPolicy 或自定义 feature extractor，必须在 `docs/task08_observation_contract.md` 和 alignment table 中写明 NavRL 代码依据、网络结构、每个分支输入 shape 和 flatten/concat 方式。

## 7. Action：严格参考 NavRL velocity-style action semantics

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

如果 action/control tracking 不稳定，先修 action/control，不要先调 reward。

## 8. Reward：严格参考 NavRL code structure，数值按 PyBullet 定标

Reward 结构应严格参考 NavRL 训练代码中的 safe navigation reward 结构，而不是自由发明。

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
NavRL reward code term -> PIRL-NavRL reward term mapping
initial coefficient source or rationale from NavRL code/config when available
which coefficients are strictly referenced
which are scaled for PyBullet and why
reward term statistics before/after tuning
reason for every coefficient change
final candidate / validated / frozen status
```

Reward 系数不能无限调。TASK_08 允许一次 NavRL-aligned scaling adaptation：

```text
NavRL code/config candidate weights
-> PyBullet scale normalization
-> easy curriculum diagnostics
-> evidence-based one-time adjustment
-> freeze or mark blocked
```

如果一次 adjustment 后仍无 learning signal，必须 blocked 或回到 diagnosed module，不得继续盲调。

## 9. Forest curriculum：严格参考 NavRL random forest 训练思路

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

必须新增：

```text
configs/task08_navrl_forest_curriculum.json
```

该配置必须给出具体数值，不得只写字段名：

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

## 10. NavRL-style high-density target，不直接从 target 起训

NavRL 可以在更大并行规模和成熟训练栈下使用高密度森林。TASK_08 应定义 NavRL-style target levels，但训练从 PyBullet-compatible easy / medium 开始。

正确路线：

```text
small/easy forest for learning signal validation
-> medium forest for curriculum growth
-> hard forest for robustness
-> target forest for NavRL-style density stress test
```

不得用降低 eval 难度制造成功。eval seeds 和 level 配置必须固定记录。

## 11. Training protocol and budget

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

`configs/task08_training_budget.json` 必须明确：

```text
smoke_steps
debug_train_steps
full_train_steps
num_envs
num_seeds
checkpoint interval under ignored outputs
promotion criteria
blocked criteria
```

要求：

```text
smoke only checks dependencies and interfaces
train writes training_completion_status.json
eval uses fixed seeds and fixed level configs
blocked writes docs/TASK_08_BLOCKED_REPORT.md
no checkpoints, outputs, videos, tensorboard, wandb committed
```

## 12. Promotion / blocked criteria

新增：

```text
docs/task08_promotion_block_criteria.md
```

最小晋级标准：

```text
heuristic mean final_distance < random mean final_distance
trained mean final_distance < random mean final_distance
trained collision rate <= random collision rate + documented tolerance
trained timeout rate not materially worse than random
reward curve is not collapsed
action clipping fraction below documented threshold
obs/lidar/dynamic/latent stats finite and non-degenerate
```

如果不满足，不能进入更难 level，必须写 blocked reason 或修复对应模块。

## 13. Random / heuristic / trained evaluation

每个关键 level 至少评估：

```text
random policy
heuristic policy
trained PPO policy
```

判断逻辑：

```text
heuristic beats random -> scene/action/observation likely feasible
trained beats random -> learning signal exists
trained approaches heuristic on easy -> training stack is usable
heuristic fails -> suspect scene/action/observation/control
heuristic succeeds but trained fails -> suspect reward/PPO/observation scaling
```

Heuristic 不是论文 baseline，只是 sanity check。

## 14. Camera / depth boundary

NavRL 实机可以使用 RGB-D/depth perception，但 Task08 不做真实 RGB-D perception stack。

Task08 使用 PyBullet/scenario raycast 来模拟 NavRL policy 输入前的结构化中间表示。

明确禁止：

```text
raw RGB policy input
raw RGB-D policy input
CNN vision encoder as Task08 mainline
```

Camera 只能作为 diagnostic / visualization，不参与 Task08 policy 输入。

## 15. Safety shield boundary

Task08 只保留 safety shield placeholder / interface，不实现正式 shield。

允许实现：

```text
policy_output -> identity_safety_filter -> action_adapter
```

正式 NavRL-style safety shield adaptation 放到 TASK_09。

## 16. 训练成功不只看步数

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

## 17. Top-down replay

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

不要提交 GIF / MP4 / outputs。

## 18. Reports

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
which NavRL code files/configs were studied
what is strictly aligned with NavRL code
what is adapted for PyBullet scale
how latent semantic obstacles extend NavRL
Task07 failure analysis summary
observation schema and stats
reward alignment and final weights
curriculum numeric levels and fixed eval seeds
random / heuristic / trained comparison
training curves and diagnostics
top-down replay cases
whether Task09 can start
```

## 19. 验收标准

TASK_08 完成时必须满足：

1. `pytest -q` 通过；
2. `docs/task08_navrl_source_index.md` 完成；
3. `docs/task08_navrl_alignment_table.md` 完成；
4. `docs/TASK_08_FROM_TASK_07_FAILURE_ANALYSIS.md` 完成；
5. `docs/task08_observation_contract.md` 完成；
6. 主线 observation 使用 NavRL-style dict observation：`state / direction / lidar / dynamic_obstacle`，并明确 latent extension；
7. lidar/raycast observation 有具体配置、归一化、统计诊断；
8. dynamic_obstacle features 有 K、排序、padding、mask、归一化；
9. latent semantic dynamic obstacle features 不泄露未来 trigger label；
10. semantic classes 有明确定义；
11. action 仍为 velocity-style，并有 tracking diagnostics；
12. reward structure 对齐 NavRL code-style safe navigation reward，并记录系数来源和调整证据；
13. forest curriculum 有具体 numeric config，包含 static / dynamic / latent semantic / mixed target；
14. training budget 有具体 steps / seeds / envs / promotion / blocked criteria；
15. 不直接从 target forest 起训；
16. fixed eval seeds 和 fixed level configs 已记录；
17. random / heuristic / trained 对比完成；
18. 至少 easy static / dynamic / latent semantic levels 显示 learning signal，或写清 blocked reason；
19. 训练结果有 top-down replay 或 fallback summary；
20. 如果没有达到预期效果，必须写 blocked report，而不是继续盲调；
21. 不提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 20. 明确不做

TASK_08 不做：

```text
formal paper success-rate table
full sim-to-real experiment
real RGB-D perception stack
EGO baseline
PIRL final risk module
NavRL reproduction claim
formal NavRL benchmark reproduction
```

TASK_08 完成后，如果 NavRL-aligned curriculum 能稳定学习，下一阶段可以进入：

```text
TASK_09: NavRL-style safety shield adaptation
TASK_10: latent semantic risk / PIRL module
TASK_11: formal evaluation protocol
```
