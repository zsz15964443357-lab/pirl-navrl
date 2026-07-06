# TASK_07：Task06 Hardening with NavRL-Style Forest Training Scenes

## 1. 阶段定位

TASK_07 是对 TASK_06 的集中强化阶段。TASK_06 已经证明了 gym-pybullet-drones 训练链路、NavRL-style observation、reward profiles、VecEnv、case replay 和 gate-easy 场景训练可以跑通，但仍不能直接作为后续论文级训练基础。

TASK_07 的目标是把 TASK_06 从 diagnostic prototype 强化为后续可用的训练基础设施。它不进入 PIRL intent/risk module，不接 EGO baseline，不做正式论文实验，不报告 formal success rate，不声称复现 NavRL，不使用 NavRL checkpoint 或结果。

核心输出：

```text
cylinder-only default training geometry
NavRL-style forest-like randomized scenes
scene-scale validation before PPO
validated parameter convergence and evidence-based freeze policy
full / smoke / blocked training protocol
random / heuristic / trained sanity comparison
PyBullet top-down case replay
strict report boundary
```

## 2. 总原则：多参考 NavRL，减少自由变量

TASK_07 不应继续开放所有变量反复调参。应参考 NavRL 的训练结构，收敛成：

```text
validated default training stack + curriculum difficulty changes
```

核心顺序：

```text
NavRL-inspired candidate defaults
-> diagnostic validation
-> validated defaults
-> frozen defaults
-> curriculum training
-> evidence-based unfreeze if needed
```

冻结不是永久不可修改，而是默认稳定。只有记录验证证据后，参数才能标记为 `frozen`；只有通过明确失败诊断，才允许解冻。

## 3. 场景主线：NavRL-style forest

TASK_07 的场景生成应更接近 NavRL Isaac Sim 训练思路：

```text
forest-like randomized scenes
many simple obstacles
random start and goal
simple dynamic motion
curriculum over obstacle count, density, and speed
```

不要优先实现大量手工特殊 case，例如每个动态障碍都精确横穿 start-goal line，或者每个潜在动态障碍都精确设计触发剧情。主训练应使用简单、随机、可控、可扩展的森林式场景。

默认训练场景：

```text
static_forest
dynamic_forest
latent_dynamic_forest
```

可选支持：

```text
mixed_forest
```

`mixed_forest` 应作为 late curriculum 或 eval-first 场景，不应作为 TASK_07 的第一个训练目标。TASK_07 应先让 static_forest / dynamic_forest / latent_dynamic_forest 的 easy level 通过 freeze gate，再考虑 mixed_forest。

所有默认训练障碍必须是 cylinder。sphere / mesh / mixed-shape 只能作为 future eval variant，不能作为默认训练场景。

## 4. 三类 forest 场景

### 4.1 Static forest

```text
random start / goal
random static cylinders
controlled obstacle count
controlled density
clearance constraints
reachable path check
```

目的：训练基础几何避障和 clearance 保持。

推荐 levels：

```text
static_forest_easy: fewer cylinders, larger free space
static_forest_medium: more cylinders, moderate density
static_forest_hard: more cylinders, narrower free space
```

### 4.2 Dynamic forest

在 static forest 基础上加入 moving cylinders。默认动态规则：

```text
random initial position
random horizontal velocity direction
speed range controlled by level
boundary behavior: bounce / wrap / respawn
```

不要求每个 moving obstacle 都精确穿越 start-goal line。通过大量随机动态障碍和 curriculum 训练动态避障。

### 4.3 Latent dynamic forest

Latent dynamic forest 实现为 initially inactive dynamic cylinders。障碍物 reset 后先静止，满足 activation rule 后变成普通 moving cylinder。

默认 activation：

```text
if distance(robot, latent_obstacle) < trigger_radius:
    active = true
elif step >= random_activation_step:
    active = true
```

要求：

```text
distance trigger is primary
random delay trigger is secondary or fallback
after activation, obstacle uses simple sampled linear motion
future trigger label is not exposed directly to policy
reject samples where activation is completely irrelevant
```

推荐比例：

```text
70% distance-trigger latent obstacles
30% random-delay latent obstacles
```

## 5. 代码与配置

建议新增或更新：

```text
pirl_navrl/scenarios/forest_curriculum.py
configs/task07_forest_curriculum.json
```

配置至少包含：

```text
arena_size
training_obstacle_kind
static_obstacle_count_by_level
dynamic_obstacle_count_by_level
latent_obstacle_count_by_level
cylinder_radius_range_by_level
cylinder_height_range
dynamic_speed_range_by_level
latent_trigger_radius_range_by_level
latent_random_activation_step_range_by_level
boundary_behavior
max_episode_steps_by_level
```

## 6. Validation before PPO

### 6.1 Scene-scale validation

新增训练前场景尺度校验：

```text
validate_task07_training_scene_scale(...)
```

也可兼容提供：

```text
validate_task06_training_scene_scale(...)
```

该 validation 必须在 PPO training 前运行。失败时必须 `raise ValueError`，不能进入 PPO。

至少检查：

```text
all default obstacles are cylinders
obstacle/drone radius ratio
start/goal clearance
obstacle-obstacle spacing
free-space density is not impossible
dynamic obstacle speed ratio
cylinder height covers flight altitude
max_steps reachability
```

### 6.2 Forest scene validation

新增：

```text
validate_forest_training_scene(...)
```

至少检查：

```text
start and goal valid
start and goal not inside obstacle margins
scene is not fully blocked
coarse reachable path exists or heuristic can make progress
dynamic obstacles move inside relevant arena regions
latent obstacles can activate by distance or delay
activated latent motion is not completely irrelevant
random / heuristic rollout metrics are finite
```

如果场景完全不可达、完全没有训练意义、或 latent activation 永远无关，不能作为默认训练样本。

## 7. NavRL reference log

必须新增或更新：

```text
docs/navrl_guided_training_adjustments_task07.md
```

也可以继续扩展 `docs/navrl_guided_training_adjustments_task06.md`，但报告中必须明确 Task07 entries。

表格至少包含：

```text
NavRL reference file/module/config
Observed NavRL design
PIRL-NavRL adaptation
Affected parameter or module
Category: system / training / curriculum
Status: candidate / validated / frozen
Reason
Validation result
Next action
```

不得只写“参考 NavRL”。必须写出具体 NavRL 文件、模块、脚本或配置来源。

## 8. Parameter convergence, validation, and evidence-based freeze policy

必须新增：

```text
docs/task07_parameter_freeze_matrix.md
docs/task07_parameter_change_log.md
configs/task07_default_ppo.json
configs/task07_default_reward.json
configs/task07_default_observation.json
```

`docs/task07_parameter_freeze_matrix.md` 至少包含：

```text
Parameter
Category: system / training / curriculum
Status: candidate / validated / frozen
Default value
Validation evidence
NavRL reference
Can change after freeze?
Unfreeze condition
Change log path
```

状态含义：

```text
candidate: candidate default, may be revised during Task07 validation
validated: passed diagnostic checks, but not final frozen yet
frozen: passed freeze gate; default-stable unless evidence-based unfreeze is documented
```

不得把未经验证的参数直接标记为 frozen。

主线 observation 应优先使用 NavRL-style dict observation：

```text
state
lidar
direction
dynamic_obstacle
```

flat observation 只能作为 debug fallback。

冻结前必须记录验证证据：

```text
observation: obs_stats finite, key features not constant, lidar/dynamic features usable
reward: finite terms, no unexpected dominance, progress and clearance terms behave reasonably
action/control: desired and actual motion consistent enough, clipping not persistently saturated
PPO: no exploding loss, no immediate entropy collapse, 2-3 seeds do not fully collapse
```

### 8.1 Freeze gate with minimum quantitative checks

TASK_07 结束时，不要求正式大规模训练成功，但必须冻结默认训练栈。freeze gate 至少包含：

```text
static_forest_easy shows stable learning effect
dynamic_forest_easy shows stable learning effect
latent_dynamic_forest_easy shows stable learning effect
heuristic mean final_distance < random mean final_distance
trained mean final_distance < random mean final_distance
trained collision rate is not materially worse than random
obs/reward/action stats are finite
action clipping fraction is below a documented threshold
2-3 seeds produce non-degenerate rollouts
top-down replay behavior is reasonable
```

如果某项不满足，不能把相关参数标记为 frozen。应保留为 candidate 或 validated，并写 blocked / change log。

### 8.2 Evidence-based unfreeze rule

冻结后不是永远不能改，但必须通过明确失败诊断解冻。允许解冻的例子：

```text
observation unfreeze: dynamic or latent features are unusable, constant, or repeatedly cause late reaction failures
reward unfreeze: policy only rushes goal, only hides, freezes in place, or reward terms are badly scaled
PPO unfreeze: multiple seeds show no learning effect and PPO diagnostics show instability
action/control unfreeze: desired and actual motion diverge or action clipping remains high
```

每次解冻必须记录：

```text
changed parameter
old value
new value
evidence
NavRL reference
expected effect
validation result
whether the parameter returns to frozen status
```

## 9. Required execution order

Codex 必须按以下顺序执行，不得跳过 validation 直接训练或写 completion：

```text
Stage 1: implement forest curriculum and cylinder-only defaults
Stage 2: implement scene-scale validation and forest scene validation
Stage 3: implement default PPO / reward / observation configs
Stage 4: implement training protocol: full / smoke / blocked
Stage 5: run smoke only for dependency and interface check
Stage 6: run easy forest diagnostic validation for static/dynamic/latent
Stage 7: collect obs/reward/action/control/PPO diagnostics
Stage 8: fill parameter freeze matrix and NavRL reference log
Stage 9: run random / heuristic / trained evaluation
Stage 10: generate top-down PyBullet replay or fallback summary
Stage 11: write completion report or blocked report
```

Smoke is dependency-only and never counts as completion.

## 10. Training protocol hardening

训练脚本必须支持：

```text
--mode full
--mode smoke
--scenario-group static_forest|dynamic_forest|latent_dynamic_forest|mixed_forest
```

要求：

```text
default mode is full
smoke must be explicit
smoke checkpoint cannot be used for final case selection
each run writes training_completion_status.json
blocked full training writes a blocked report
gate-easy or smoke cannot be reported as full completion
```

建议新增：

```text
configs/task07_training_budget.json
scripts/train_task07_hardened_multiscenario.py
```

## 11. Random / heuristic / trained comparison

新增 heuristic sanity policies：

```text
goal_tracking_policy
static_clearance_heuristic_policy
dynamic_reactive_heuristic_policy
latent_reactive_heuristic_policy
```

每个 scenario group 必须评估：

```text
random policy
heuristic sanity policy
trained PPO policy
```

解释规则：

```text
heuristic fails -> suspect scene / control / reward / observation
heuristic succeeds but PPO fails -> suspect PPO / reward / observation / training config
trained beats heuristic -> policy may be learning useful behavior
```

heuristic 不是 formal baseline，不得作为论文 baseline 报告。

## 12. Top-down PyBullet renderer

必须新增真正 PyBullet top-down renderer。Matplotlib JSONL replay 可以保留，但只能作为 fallback。

建议新增：

```text
pirl_navrl/visualization/topdown_pybullet_renderer.py
scripts/render_task07_topdown_pybullet_case.py
```

要求：

```text
camera fixed above arena
camera points downward
show drone, start, goal, cylinder footprint, trajectory
show dynamic obstacle path
show latent activation state when relevant
show success/collision/timeout/failure_type
output gif or mp4 under ignored outputs
fallback summary JSON if rendering fails
```

不要提交 GIF / MP4 / checkpoints / outputs。

## 13. Diagnostics and reports

新增或更新：

```text
docs/TASK_07_TRAINING_PROTOCOL_REPORT.md
docs/TASK_07_COMPLETION_REPORT.md
```

如果 full training 未完成，新增：

```text
docs/TASK_07_BLOCKED_REPORT.md
```

报告必须说明：

```text
TASK_06 gate-easy result is diagnostic only
why scenes are NavRL-style forest-like scenes
how static/dynamic/latent forest levels differ
how latent activation works
how forest validation rejects bad samples
how curriculum changes obstacle count, density, or speed
NavRL reference log status
parameter freeze matrix status
default PPO / reward / observation validation evidence
which parameters remain curriculum variables
unfreeze records if any
random / heuristic / trained comparison
top-down PyBullet replay status
blocked items if any
```

本地 diagnostics 建议输出到 ignored `outputs/`：

```text
obs_stats.json
reward_terms_stats.json
action_stats.json
control_tracking_error.json
distance_curve.json
reachability_report.json
forest_scene_validation_report.json
parameter_validation_report.json
```

## 14. Tests

新增或更新 tests，至少覆盖：

```text
cylinder-only default training scenes
non-cylinder default scene rejected
scene-scale validation pass/fail
forest scene validation pass/fail
dynamic obstacle motion and boundary behavior
latent distance-trigger activation
latent random-delay activation
heuristic policy finite action and progress check
training mode full/smoke status schema
top-down PyBullet renderer fallback schema
parameter freeze matrix schema
parameter status candidate/validated/frozen schema
parameter change log schema
NavRL reference log schema
default PPO / reward / observation config exists
report templates contain required fields
```

## 15. 验收标准

TASK_07 完成时必须满足：

1. `pytest -q` 通过；
2. static_forest / dynamic_forest / latent_dynamic_forest 默认训练障碍全部为 cylinder；
3. scene-scale validation 在 PPO 前执行；
4. 三类 forest 场景都通过 scene-scale validation 和 forest scene validation；
5. latent_dynamic_forest 支持 distance-to-drone trigger 和可选 random-delay trigger；
6. train script 支持 full / smoke / blocked，且 smoke 不会被标记为 completed；
7. 按 Required execution order 执行；
8. NavRL reference log 完成，且含具体 NavRL 文件/模块/配置；
9. parameter freeze matrix 完成，并明确 system / training / curriculum 以及 candidate / validated / frozen 状态；
10. frozen 参数都有 validation evidence；
11. 默认 PPO / reward / observation 配置存在，并说明 NavRL 参考和验证证据；
12. 每类场景都有 random / heuristic / trained eval summary；
13. 每类都有 success 或 best_non_success case；
14. 每类都有 representative failure case；
15. 每类有 top-down PyBullet GIF/video 或明确 fallback summary；
16. 如果发生解冻，必须有 parameter change log 和 failure diagnosis；
17. TASK_06 gate-easy 结果被明确标记为 diagnostic，不是 formal result；
18. 不提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 16. 明确不做

TASK_07 不做：

```text
PIRL intent/risk module
EGO baseline
formal paper success-rate table
multi-seed paper benchmark
NavRL reproduction claim
checkpoint/result artifact submission
```

TASK_07 完成后，才能决定是否进入真正的 PIRL/risk/intention module prototype 或 frozen evaluation protocol。
