# TASK_07：Task06 Hardening with NavRL-Style Forest Training Scenes

## 0. 任务定位

TASK_07 是 TASK_06 的集中修复和强化阶段。

TASK_06 已完成 multi-scenario PPO diagnostic prototype，但审查发现它还不能直接作为后续论文级训练基础。TASK_07 的目标是修复 TASK_06 中的 geometry、scene scale、forest scenario generation、parameter convergence、training protocol、heuristic sanity、top-down PyBullet replay 和 reporting 问题。

TASK_07 不进入 PIRL intent/risk module，不做 EGO baseline，不做正式论文实验，不报告 formal success rate，不声称复现 NavRL，不使用 NavRL checkpoint 或结果，不提交 outputs/checkpoints/GIF/MP4/wandb/TensorBoard。

## 1. 必须阅读的上下文

执行前请先阅读：

```text
docs/07_task07_task06_hardening.md
docs/TASK_06_COMPLETION_REPORT.md
docs/navrl_guided_training_adjustments_task06.md
codex_tasks/TASK_06_navrl_guided_multiscenario_ppo_case_replay.md
```

TASK_06 的 gate-easy 结果只能作为 diagnostic observation，不能作为 formal result。

## 2. 核心原则：多参考 NavRL，减少自由变量

TASK_07 不应继续开放所有变量反复调参。必须参考 NavRL 的训练结构，收敛成：

```text
fixed default training stack + curriculum difficulty changes
```

默认场景必须优先实现更接近 NavRL Isaac Sim 训练思路的随机森林式训练场景：

```text
static_forest
dynamic_forest
latent_dynamic_forest
mixed_forest optional
```

核心场景原则：

```text
simple forest-like randomized scenes + obstacle-count curriculum + speed/density curriculum
```

核心参数原则：

```text
freeze observation / reward / PPO / action-control defaults after Task7
later training changes curriculum parameters first
unfreeze PPO or reward only with documented failure diagnosis
```

不要把 TASK_07 做成一堆复杂手工小场景，也不要让 Codex 在没有诊断证据时随意改 PPO / reward / observation。

## 3. Cylinder-only default training geometry

必须修复 TASK_06 默认训练 geometry。

要求：

- 默认训练障碍全部为 `cylinder`；
- static_forest / dynamic_forest / latent_dynamic_forest 中所有默认 obstacle kind == `cylinder`；
- sphere / mesh / mixed-shape 只能作为 future eval variant；
- 不允许默认训练场景继续使用 sphere；
- 更新 tests，断言所有默认训练 obstacle kind == `cylinder`。

## 4. Forest curriculum implementation

新增或更新：

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

## 5. Static forest

实现随机静态圆柱森林：

```text
random start / goal
random static cylinders
controlled obstacle count and density
clearance constraints
reachability check
```

不要求手工设计 path-near / gate / cluster 类型，但场景不能完全无避障意义，也不能完全堵死。

推荐 levels：

```text
static_forest_easy
static_forest_medium
static_forest_hard
```

## 6. Dynamic forest

在 static forest 基础上加入 moving cylinders。

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
dynamic_forest_easy
dynamic_forest_medium
dynamic_forest_hard
```

## 7. Latent dynamic forest

潜在动态障碍实现为 initially inactive dynamic cylinders。

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
latent_forest_easy
latent_forest_medium
latent_forest_hard
```

## 8. Scene-scale validation

新增训练前 scene-scale validation：

```text
validate_task07_training_scene_scale(...)
```

可以兼容提供：

```text
validate_task06_training_scene_scale(...)
```

必须在 PPO training 前调用。失败时必须 `raise ValueError`，不得进入 PPO。

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

所有 scale 设置都要参考 NavRL，并记录具体 NavRL 文件/config 到 `docs/navrl_guided_training_adjustments_task06.md` 或新增 `docs/navrl_guided_training_adjustments_task07.md`。

## 9. Forest validation

新增：

```text
validate_forest_training_scene(...)
```

至少检查：

```text
start and goal valid
not inside obstacle margins
not fully blocked
coarse reachable path exists or heuristic can make progress
dynamic obstacles move in relevant arena region
latent obstacles can activate by distance or delay
activated latent motion is not completely irrelevant
rollout metrics are finite
```

不要求每个动态障碍都精确横穿 start-goal line；只要求整体随机场景有训练意义、可达、有避障压力。

## 10. Parameter convergence and freeze policy

新增：

```text
docs/task07_parameter_freeze_matrix.md
configs/task07_default_ppo.json
configs/task07_default_reward.json
configs/task07_default_observation.json
```

`docs/task07_parameter_freeze_matrix.md` 必须包含：

```text
Parameter
Category: frozen / tune_once / curriculum
Default value
NavRL reference
Allowed to change after Task7?
Change condition
```

### Frozen after Task7

以下内容应冻结，后续不得随意修改：

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

flat observation 只能作为 debug fallback。

### Tune once in Task7

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

默认 PPO / policy stack 必须参考 NavRL 的训练结构和参数尺度，并记录对应 NavRL 文件、脚本或 config。

### Curriculum variables

TASK_07 之后，后续训练主要允许变化：

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

后续融合场景训练默认先调 curriculum，不调 PPO / reward / observation / action。只有 `docs/TASK_07_BLOCKED_REPORT.md` 或后续 failure report 明确证明默认训练栈有问题时，才允许解冻。

### Freeze gate

TASK_07 结束时，不要求正式大规模训练成功，但必须冻结默认训练栈。冻结 gate：

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

## 11. Training protocol hardening

新增或修复训练脚本，使其支持：

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
- gate-easy 或 smoke 结果不得冒充完整 Task 7 completion。

可以新增：

```text
configs/task07_training_budget.json
scripts/train_task07_hardened_multiscenario.py
```

也可以扩展现有 TASK_06 训练脚本，但必须保持 TASK_06 历史结果可解释。

## 12. Random / heuristic / trained 三方对比

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

## 13. Top-down PyBullet renderer

当前 Matplotlib JSONL replay 可保留为 fallback，但 TASK_07 必须新增真正 PyBullet top-down renderer。

新增：

```text
pirl_navrl/visualization/topdown_pybullet_renderer.py
scripts/render_task07_topdown_pybullet_case.py
```

要求：

- camera fixed above arena and points downward；
- show drone, start, goal, cylinder footprint, trajectory；
- show dynamic obstacle path；
- show latent activation state when relevant；
- show success/collision/timeout/failure_type；
- output GIF or MP4 under ignored outputs；
- if rendering fails, write fallback summary JSON with reason。

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

Reports 必须说明：

- TASK_06 gate-easy result 是 diagnostic，不是 formal result；
- why the new scenes are NavRL-style forest-like scenes；
- how static/dynamic/latent forest levels differ；
- how latent activation works；
- how forest validation rejects bad samples；
- how curriculum changes obstacle count, density, or speed；
- parameter freeze matrix 是否完成；
- 默认 PPO / reward / observation 是否冻结；
- 哪些参数后续只能作为 curriculum 变化；
- 每类场景 random / heuristic / trained 对比；
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

TASK_07 完成后，再决定是否进入 PIRL/risk/intention module prototype 或 frozen evaluation protocol。