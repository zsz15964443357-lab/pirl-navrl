# TASK_07：Task06 Hardening for Paper-Ready Multi-Scenario Training

## 1. 阶段定位

TASK_07 是对 TASK_06 的专门强化与修复阶段。

TASK_06 已经完成了一个有价值的多场景 PPO diagnostic prototype：它证明了 gym-pybullet-drones 训练链路、NavRL-style observation、reward profiles、VecEnv、case replay 和 gate-easy 场景训练可以跑通。但 TASK_06 仍不能直接作为后续论文级训练基础。TASK_07 的目标是把 TASK_06 暴露出的场景、尺度、训练协议、可达性、可视化和报告问题集中修复。

TASK_07 不进入 PIRL intent/risk module，不接 EGO baseline，不做正式论文实验，不报告 formal success rate，不声称复现 NavRL，不使用 NavRL checkpoint 或结果。

TASK_07 的输出应该让后续工作具备可信基础：

```text
cylinder-only training geometry
scene-scale validation
interaction-driven scenario design
full/smoke/blocked training protocol
random / heuristic / trained sanity comparison
PyBullet top-down case replay
strict report boundary
```

## 2. 需要解决的核心问题

TASK_07 主要修复以下问题：

1. TASK_06 默认训练场景仍有 sphere / cylinder 混用；
2. 缺少训练前 scene-scale validation；
3. full / smoke / blocked training protocol 没有完全落地；
4. 缺少 heuristic sanity policy，无法判断场景和控制接口是否可达；
5. 当前 GIF 主要是 Matplotlib JSONL replay，而不是真正 PyBullet top-down camera replay；
6. gate-easy 成功和完整多场景训练完成之间的边界需要更严格；
7. 静态、动态、潜在动态场景必须体现真实避障交互，而不是只是场景里存在障碍物。

## 3. Cylinder-only 默认训练几何

TASK_07 必须把默认训练几何统一为 cylinder：

```text
static obstacle kind = cylinder
dynamic obstacle kind = cylinder
latent_dynamic obstacle kind = cylinder
```

要求：

- 修改 `pirl_navrl/scenarios/dynamic_curriculum.py`；
- static / dynamic / latent_dynamic 默认训练障碍全部使用 cylinder；
- sphere / mesh / mixed-shape 只能作为 future eval variant，不能作为 TASK_07 默认训练场景；
- tests 必须断言默认训练场景的所有 obstacle kind 都是 `cylinder`。

## 4. Scene-scale validation

TASK_07 必须新增训练前场景尺度校验，例如：

```text
validate_task07_training_scene_scale(...)
```

也可以沿用兼容命名：

```text
validate_task06_training_scene_scale(...)
```

该 validation 必须在 PPO training 前运行。失败时必须 `raise ValueError`，不能进入 PPO。

至少检查：

```text
obstacle/drone radius ratio
start/goal clearance
obstacle-obstacle spacing
corridor passability
dynamic obstacle speed ratio
cylinder height covers flight altitude
max_steps reachability
```

必须补充或更新配置字段：

```text
training_obstacle_kind
drone_collision_radius
safety_margin
cylinder_radius_range_by_group
cylinder_height_range
obstacle_drone_radius_ratio_range
min_start_goal_clearance
min_obstacle_obstacle_clearance
min_corridor_width
dynamic_obstacle_speed_range
dynamic_to_drone_speed_ratio_range
max_episode_steps_by_group
```

场景尺度应参考 NavRL，并记录在：

```text
docs/navrl_guided_training_adjustments_task06.md
```

## 5. Interaction-driven scenario design

TASK_07 场景必须体现避障交互，而不是只是存在障碍物。

核心原则：

```text
A scenario is invalid if the obstacle does not meaningfully affect the nominal start-goal path.
```

### 5.1 Static 场景

静态障碍应放在 start-goal corridor 附近，让直线飞行存在 collision 或 near-miss 风险，但仍保留可行绕行空间。

要求：

```text
one or more cylinders near the nominal path
not fully blocking the path
clear bypass corridor exists
straight-line or goal-tracking policy has low-clearance risk
clearance heuristic should improve min_clearance
```

推荐 easy 场景：

```text
one cylinder near the path centerline, offset enough to be passable
```

推荐 medium 场景：

```text
two or three cylinders forming a narrower but passable corridor
```

### 5.2 Dynamic 场景

动态障碍必须穿过无人机 nominal path，并且 timing 要接近无人机到达交汇区域的时间。

要求：

```text
moving cylinder crosses the start-goal corridor
crossing point near the middle of the route
crossing time overlaps expected drone arrival time
straight-line policy should encounter near-miss/collision risk
reactive heuristic should slow down, wait, or deviate
```

动态障碍不能只是远处移动，否则不能体现避障效果。

### 5.3 Latent dynamic 场景

潜在动态障碍默认应使用距离触发，而不是无关的固定 step 触发。

要求：

```text
trigger_mode = distance_to_drone
trigger_radius configurable
fallback_trigger_step optional only as safety fallback
obstacle initially stationary or low-risk
when drone enters trigger_radius, obstacle begins crossing the path
future trigger label is not exposed directly to policy
```

潜在动态场景要体现：无人机靠近后，障碍突然启动，策略是否能减速、绕行或保持 clearance。

推荐 easy 场景：

```text
latent cylinder starts beside the corridor
trigger_radius around 1.2m to 1.8m
then crosses the corridor at moderate speed
```

推荐 medium 场景：

```text
smaller trigger radius
shorter reaction window
obstacle starts closer to the corridor
```

## 6. Avoidance interaction validation

TASK_07 必须新增：

```text
validate_avoidance_interaction(...)
```

至少检查：

```text
static obstacle near the nominal start-goal corridor
dynamic obstacle path crosses the drone corridor
dynamic crossing time overlaps expected drone arrival time
latent obstacle is distance-triggered by drone approach
latent obstacle crosses the corridor after trigger
straight-line policy is meaningfully risky
heuristic avoidance policy is safer than straight-line policy
```

如果场景不体现避障交互，不能作为默认训练场景。

## 7. Training protocol hardening

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
--scenario-group static|dynamic|latent_dynamic|mixed_static_dynamic
```

要求：

- 默认 `--mode full`；
- smoke 只能显式指定；
- smoke checkpoint 不得用于 final case selection；
- 每个 run 必须写 `training_completion_status.json`；
- full 未完成时必须写 blocked report；
- 不能用 gate-easy 或 smoke 结果冒充完整 Task 7 completion。

## 8. Random / heuristic / trained 三方对比

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

## 9. Top-down PyBullet renderer

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
show latent trigger state when relevant
show success/collision/timeout/failure_type
output gif or mp4 under outputs/task07 or outputs/task06 review folder
fallback summary JSON if rendering fails
```

不要提交 GIF / MP4 / checkpoints / outputs。

## 10. Diagnostics and blocked reports

TASK_07 必须保留诊断证据，但不提交 outputs。

建议本地产物：

```text
obs_stats.json
reward_terms_stats.json
action_stats.json
control_tracking_error.json
distance_curve.json
reachability_report.json
interaction_validation_report.json
```

blocked report 必须具体，不能只写“训练失败”。

`docs/TASK_07_BLOCKED_REPORT.md` 至少包含：

```text
exact command
timesteps reached
failure mode or error summary
diagnostic metrics
NavRL references consulted
fixes attempted
next required change
whether outputs are smoke-only or full-training partial
```

## 11. Reports

新增：

```text
docs/TASK_07_TRAINING_PROTOCOL_REPORT.md
docs/TASK_07_COMPLETION_REPORT.md
```

报告必须明确：

- TASK_06 gate-easy result 是 diagnostic，不是 formal result；
- TASK_07 是否完成 cylinder-only；
- scene-scale validation 是否在 PPO 前执行；
- interaction validation 是否证明静态/动态/潜在动态场景确实体现避障；
- 每类场景 random / heuristic / trained 对比结果；
- top-down PyBullet replay 是否生成；
- 哪些内容仍 blocked。

## 12. Tests

新增或更新 tests，至少覆盖：

```text
cylinder-only default training scenes
non-cylinder default scene rejected
scene-scale validation pass/fail
corridor passability validation
dynamic crossing interaction validation
latent distance-trigger activation
straight-line policy risky check
heuristic policy finite action and safer-than-straight check
training mode full/smoke status schema
top-down PyBullet renderer fallback schema
report templates contain required fields
```

## 13. 验收标准

TASK_07 完成时必须满足：

1. `pytest -q` 通过；
2. static / dynamic / latent_dynamic 默认训练障碍全部为 cylinder；
3. scene-scale validation 在 PPO 前执行；
4. static / dynamic / latent_dynamic 都通过 scene-scale validation；
5. static / dynamic / latent_dynamic 都通过 avoidance interaction validation；
6. latent_dynamic 默认采用 distance-to-drone trigger，fixed step trigger 只能作为 fallback；
7. train script 支持 full / smoke / blocked 状态；
8. smoke 不会被标记为 completed；
9. 每类场景都有 random / heuristic / trained eval summary；
10. 每类都有 success 或 best_non_success case；
11. 每类都有 representative failure case；
12. 每类有 top-down PyBullet GIF/video 或明确 fallback summary；
13. TASK_06 gate-easy 结果被明确标记为 diagnostic，不是 formal result；
14. 不提交 outputs、checkpoints、GIF、MP4、TensorBoard、wandb。

## 14. 明确不做

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