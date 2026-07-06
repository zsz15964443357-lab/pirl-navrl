# TASK_07 Update：NavRL-Style Forest Scene Requirement

## 1. 执行优先级

执行 TASK_07 时，Codex 必须同时读取：

```text
docs/07_task07_task06_hardening.md
codex_tasks/TASK_07_task06_hardening_training_protocol.md
docs/07_task07_navrl_style_forest_scene_update.md
```

如果原 TASK_07 文件里的场景描述和本文件冲突，以本文件为准。

## 2. 关键变化

TASK_07 的默认场景不应优先实现大量手工特殊 case。

应优先实现更接近 NavRL Isaac Sim 训练思路的随机森林式训练场景：

```text
static_forest
dynamic_forest
latent_dynamic_forest
mixed_forest optional
```

核心原则：

```text
simple forest-like randomized scenes + obstacle-count curriculum + speed/density curriculum
```

## 3. Static forest

实现随机静态圆柱森林：

```text
random start / goal
random static cylinders
controlled obstacle count and density
clearance constraints
reachability check
```

不要求手工设计 path-near / gate / cluster 类型，但场景不能完全无避障意义。

## 4. Dynamic forest

在 static forest 基础上加入 moving cylinders。

默认动态规则：

```text
random initial position
random horizontal velocity direction
speed range controlled by level
boundary behavior: bounce / wrap / respawn
```

不要求每个 moving obstacle 都精确穿越 start-goal line。通过大量随机动态障碍和 curriculum 训练动态避障。

## 5. Latent dynamic forest

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

## 6. Forest validation

新增或替换为：

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

## 7. Config requirement

新增或更新：

```text
configs/task07_forest_curriculum.json
```

包含：

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

默认训练障碍仍必须全部是 cylinder。

## 8. 保留原硬性要求

本更新不取消以下要求：

```text
scene-scale validation before PPO
full / smoke / blocked protocol
random / heuristic / trained comparison
PyBullet top-down replay or fallback
TASK_06 gate-easy result is diagnostic only
no output artifacts committed
pytest -q passes
```

## 9. 验收

TASK_07 完成时必须能说明：

```text
why the new scenes are NavRL-style forest-like scenes
how static/dynamic/latent forest levels differ
how latent activation works
how forest validation rejects bad samples
how curriculum changes obstacle count, density, or speed
```

不要把 TASK_07 做成一堆复杂手工小场景。