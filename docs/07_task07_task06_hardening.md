# TASK_07：Task06 Hardening with NavRL-Style Forest Training Scenes

## 1. 阶段定位

TASK_07 是对 TASK_06 的集中强化阶段。TASK_06 已经证明了 gym-pybullet-drones 训练链路、NavRL-style observation、reward profiles、VecEnv、case replay 和 gate-easy 场景训练可以跑通，但仍不能直接作为后续论文级训练基础。

TASK_07 的目标是把 TASK_06 从 diagnostic prototype 强化为后续可用的训练基础设施。它不进入 PIRL intent/risk module，不接 EGO baseline，不做正式论文实验，不报告 formal success rate，不声称复现 NavRL，不使用 NavRL checkpoint 或结果。

TASK_07 的核心输出：

```text
cylinder-only default training geometry
NavRL-style forest-like randomized scenes
scene-scale validation before PPO
parameter convergence and freeze policy
full / smoke / blocked training protocol
random / heuristic / trained sanity comparison
PyBullet top-down case replay
strict report boundary
```

## 2. 场景主线：NavRL-style forest，而不是复杂手工小场景

TASK_07 的场景生成应更接近 NavRL Isaac Sim 训练思路：

```text
forest-like randomized scenes
many simple obstacles
random start and goal
simple dynamic motion
curriculum over obstacle count, density, and speed
```

不要优先实现大量手工特殊 case，例如每个动态障碍都精确横穿 start-goal line，或者每个潜在动态障碍都精确设计触发剧情。主训练应使用简单、随机、可控、可扩展的森林式场景。

核心原则：

```text
Use NavRL-style forest-like randomized training scenes rather than many hand-designed special cases.
```

## 3. 三类默认训练场景

默认训练场景重构为：

```text
static_forest
dynamic_forest
latent_dynamic_forest
```

可选支持：

```text
mixed_forest
```

所有默认训练障碍必须是 cylinder。sphere / mesh / mixed-shape 只能作为 future eval variant，不能作为默认训练场景。

## 4. Static forest

Static forest 是随机圆柱森林：

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

不要求手工设计 path-near / gate / cluster 类型，但场景不能完全无避障意义，也不能完全堵死。

## 5. Dynamic forest

Dynamic forest 在 static forest 基础上加入 moving cylinders。

默认动态规则：

```text
random initial position
random horizontal velocity direction
speed range controlled by level
boundary behavior: bounce / wrap / respawn
```

不要求每个 moving obstacle 都精确穿越 start-goal line。通过大量随机动态障碍和 curriculum 训练动态避障。

推荐 levels：

```text
dynamic_forest_easy: few moving cylinders, slow speed
dynamic_forest_medium: more moving cylinders, medium speed
dynamic_forest_hard: more moving cylinders, faster speed
```

## 6. Latent dynamic forest

Latent dynamic forest 实现为 initially inactive dynamic cylinders。

障碍物 reset 后先静止，满足 activation rule 后变成普通 moving cylinder。

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

推荐 levels：

```text
latent_forest_easy: few latent cylinders, larger trigger radius, slow speed
latent_forest_medium: more latent cylinders, smaller trigger radius, medium speed
latent_forest_hard: more latent cylinders, shorter reaction window, faster speed
```

## 7. 代码与配置建议

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

## 8. Scene-scale validation

TASK_07 必须新增训练前场景尺度校验，例如：

```text
validate_task07_training_scene_scale(...)
```

也可以兼容提供：

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

场景尺度应参考 NavRL，并记录在 `docs/navrl_guided_training_adjustments_task06.md` 或新增 `docs/navrl_guided_training_adjustments_task07.md`。

## 9. Forest scene validation

TASK_07 不需要强制每个障碍物都手工穿越 start-goal corridor，但必须验证随机森林场景不是无效样本。

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

## 10. Parameter convergence and freeze policy

TASK_07 必须把“可变项太多”的问题收敛下来。目标不是继续无限调参，而是参考 NavRL 建立一套默认训练栈，然后主要通过 curriculum 改变场景难度。

必须新增：

```text
docs/task07_parameter_freeze_matrix.md
configs/task07_default_ppo.json
configs/task07_default_reward.json
configs/task07_default_observation.json
```

`docs/task07_parameter_freeze_matrix.md` 至少包含以下列：

```text
Parameter
Category: frozen / tune_once / curriculum
Default value
NavRL reference
Allowed to change after Task7?
Change condition
```

### 10.1 Frozen parameters

以下内容应在 TASK_07 中尽快冻结，后续不得随意修改：

```text
observation schema
action format
policy architecture family
collision radius
safety margin
success radius
collision/success condition
control frequency
max_speed default
top-down replay schema
```

主线 observation 应优先使用 NavRL-style dict observation：

```text
state
lidar
direction
dynamic_obstacle
```

flat observation 只保留为 debug fallback。

### 10.2 Tune-once parameters

以下内容可在 TASK_07 中短期调一次，形成默认配置后冻结：

```text
PPO learning_rate
PPO n_steps
batch_size
gamma
gae_lambda
clip_range
ent_coef
VecNormalize setting
reward weights
action penalty
clearance penalty
collision penalty
progress weight
```

默认 PPO / policy stack 应密切参考 NavRL 的训练结构和参数尺度。可以使用 SB3 适配，但必须记录对应 NavRL 文件或 config。

### 10.3 Curriculum parameters

TASK_07 之后，后续训练主要允许变化 curriculum 参数：

```text
arena size
goal distance
static obstacle count
dynamic obstacle count
latent obstacle count
obstacle density
dynamic speed range
latent trigger radius
episode horizon
```

后续融合场景训练中，默认规则是：先固定 observation / reward / PPO / action / control，再调 curriculum。只有有明确 failure diagnosis 时，才允许解冻 PPO 或 reward。

### 10.4 Freeze gate

TASK_07 结束时，不要求完成正式大规模训练，但必须冻结默认训练栈。冻结 gate：

```text
static_forest_easy shows stable learning effect
dynamic_forest_easy shows stable learning effect
latent_dynamic_forest_easy shows stable learning effect
heuristic policy clearly beats random
trained policy is not clearly worse than heuristic and should beat random
reward/obs/action diagnostics show no NaN, saturation, or scale anomaly
2-3 seeds do not fully collapse under the same default stack
top-down replay behavior is reasonable
```

冻结后，除非 blocked report 明确证明默认训练栈有问题，否则不得继续随意调 PPO / reward / observation / action。

## 11. Training protocol hardening

TASK_07 必须明确区分：

```text
smoke
full
blocked
```

建议新增：

```text
configs/task07_training_budget.json
scripts/train_task07_hardened_multiscenario.py
```

或修复 TASK_06 训练脚本，使其支持：

```text
--mode full
--mode smoke
--scenario-group static_forest|dynamic_forest|latent_dynamic_forest|mixed_forest
```

要求：

- 默认 `--mode full`；
- smoke 只能显式指定；
- smoke checkpoint 不得用于 final case selection；
- 每个 run 必须写 `training_completion_status.json`；
- full 未完成时必须写 blocked report；
- 不能用 gate-easy 或 smoke 结果冒充完整 Task 7 completion。

## 12. Random / heuristic / trained 三方对比

TASK_07 必须新增 heuristic sanity policies，用于检查场景和控制接口是否合理。

推荐 policies：

```text
goal_tracking_policy
static_clearance_heuristic_policy
dynamic_reactive_heuristic_policy
latent_reactive_heuristic_policy
```

每类场景至少 eval：

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

heuristic 不是 formal baseline，不得作为论文 baseline 宣称。

## 13. Top-down PyBullet renderer

TASK_07 必须新增真正 PyBullet top-down renderer。Matplotlib JSONL replay 可以保留，但只能作为 fallback。

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

## 14. Diagnostics and reports

新增或更新：

```text
docs/TASK_07_TRAINING_PROTOCOL_REPORT.md
docs/TASK_07_COMPLETION_REPORT.md
```

如果 full training 未完成，新增：

```text
docs/TASK_07_BLOCKED_REPORT.md
```

报告必须明确：

- TASK_06 gate-easy result 是 diagnostic，不是 formal result；
- TASK_07 是否完成 cylinder-only；
- scene-scale validation 是否在 PPO 前执行；
- forest scene validation 是否证明场景可达且有训练意义；
- parameter freeze matrix 是否完成；
- 默认 PPO / reward / observation 是否冻结；
- 哪些参数仍允许作为 curriculum 变化；
- 每类场景 random / heuristic / trained 对比结果；
- top-down PyBullet replay 是否生成；
- 哪些内容仍 blocked。

本地 diagnostics 建议输出到 ignored `outputs/`：

```text
obs_stats.json
reward_terms_stats.json
action_stats.json
control_tracking_error.json
distance_curve.json
reachability_report.json
forest_scene_validation_report.json
```

## 15. Tests

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
default PPO / reward / observation config exists
report templates contain required fields
```

## 16. 验收标准

TASK_07 完成时必须满足：

1. `pytest -q` 通过；
2. static_forest / dynamic_forest / latent_dynamic_forest 默认训练障碍全部为 cylinder；
3. scene-scale validation 在 PPO 前执行；
4. 三类 forest 场景都通过 scene-scale validation；
5. 三类 forest 场景都通过 forest scene validation；
6. latent_dynamic_forest 默认支持 distance-to-drone trigger，并可选 random-delay trigger；
7. train script 支持 full / smoke / blocked 状态；
8. smoke 不会被标记为 completed；
9. 每类场景都有 random / heuristic / trained eval summary；
10. 每类都有 success 或 best_non_success case；
11. 每类都有 representative failure case；
12. 每类有 top-down PyBullet GIF/video 或明确 fallback summary；
13. parameter freeze matrix 完成，并明确 frozen / tune_once / curriculum 三类；
14. 默认 PPO / reward / observation 配置存在，并说明 NavRL 参考；
15. TASK_06 gate-easy 结果被明确标记为 diagnostic，不是 formal result；
16. 不提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 17. 明确不做

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